import logging
import secrets
from django.http import HttpResponseForbidden
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
import hmac
import hashlib
from django_ratelimit.decorators import ratelimit

# Import the Integration model we defined previously
from apps.integrations.models import Integration
from apps.integrations.github.oauth import GitHubOAuth
from apps.audits.tasks import run_audit_task

logger = logging.getLogger(__name__)

class GithubConnectView(APIView):
    """
    Step 1: Generates the GitHub OAuth URL.
    The frontend should redirect the user to this URL.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Check if GitHub OAuth credentials are configured
            if not hasattr(settings, 'GITHUB_CLIENT_ID') or not settings.GITHUB_CLIENT_ID:
                logger.error("GITHUB_CLIENT_ID is not configured in settings")
                return Response(
                    {"error": "GitHub integration is not configured. Please contact your administrator."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            if not hasattr(settings, 'GITHUB_CLIENT_SECRET') or not settings.GITHUB_CLIENT_SECRET:
                logger.error("GITHUB_CLIENT_SECRET is not configured in settings")
                return Response(
                    {"error": "GitHub integration is not configured. Please contact your administrator."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            oauth = GitHubOAuth()
            # Ensure this matches the callback URL registered in your GitHub App settings
            redirect_uri = f"{settings.FRONTEND_URL}/integrations/github/callback" 
            
            # Generate a cryptographically strong random string
            state = secrets.token_hex(16)
            # Store this string in the user's session
            request.session['github_oauth_state'] = state
            
            # Get base auth URL
            url = oauth.get_authorization_url(redirect_uri)
            
            # Append state to the URL parameters
            # valid since oauth.get_authorization_url already adds params with '?'
            final_url = f"{url}&state={state}"
            
            return Response({
                "authorization_url": final_url, 
                "state": state
            })
        except AttributeError as e:
            logger.error(f"GitHub OAuth configuration error: {e}")
            return Response(
                {"error": "GitHub integration is not properly configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Unexpected error in GitHub connect: {e}", exc_info=True)
            return Response(
                {"error": "Failed to generate GitHub OAuth URL. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


from rest_framework import viewsets
from apps.integrations.serializers import IntegrationSerializer

class IntegrationViewSet(viewsets.ModelViewSet):
    """
    API for managing Integrations.
    Strictly enforcing "only GitHub" for V1.
    """
    serializer_class = IntegrationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Users see integrations for their organization
        if hasattr(self.request, 'organization') and self.request.organization:
             return Integration.objects.filter(organization=self.request.organization)
        # Fallback if organization middleware isn't perfect or for superusers
        return Integration.objects.none()

    def perform_create(self, serializer):
        # Strict guardrail: Always set provider='github'
        # The logic is also in serializer but double enforcement is safer
        serializer.save(
            provider='github', 
            organization=self.request.organization,
            created_by=self.request.user
        )


class GithubCallbackView(APIView):
    """
    Step 2: Receives the 'code' from the Frontend, exchanges it for a token,
    and creates/updates the Integration record.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # 1. CSRF / State Verification
        state_from_get = request.query_params.get('state')
        stored_state = request.session.get('github_oauth_state')

        if not stored_state or state_from_get != stored_state:
            return HttpResponseForbidden("CSRF Verification Failed.")
        
        # Clean up session
        del request.session['github_oauth_state']

        code = request.data.get("code")
        
        if not code:
            return Response({"error": "No code provided"}, status=status.HTTP_400_BAD_REQUEST)

        oauth = GitHubOAuth()
        
        # Get the redirect_uri that was used in the authorization request
        # It must match exactly what was registered in GitHub OAuth App
        redirect_uri = f"{settings.FRONTEND_URL}/integrations/github/callback"
        
        # 1. Exchange Code for Access Token
        try:
            token_data = oauth.exchange_code_for_token(code, redirect_uri=redirect_uri)
        except Exception as e:
            logger.error(f"GitHub Token Exchange Failed: {e}")
            return Response({"error": "Failed to connect to GitHub"}, status=status.HTTP_502_BAD_GATEWAY)

        if "error" in token_data:
            return Response({"error": token_data.get("error_description")}, status=status.HTTP_400_BAD_REQUEST)

        access_token = token_data.get('access_token')
        # refresh_token = token_data.get('refresh_token') # GitHub Apps usually have this, OAuth Apps might not

        # 2. Get GitHub User ID (stable identifier)
        # We need this to ensure we don't duplicate integrations if the user reconnects
        try:
            gh_user = oauth.get_user_info(access_token)
        except Exception as e:
            logger.error(f"GitHub User Info Failed: {e}")
            return Response({"error": "Failed to fetch GitHub user profile"}, status=status.HTTP_502_BAD_GATEWAY)

        external_id = str(gh_user['id'])
        gh_username = gh_user['login']

        # 3. Resolve Organization
        # Assuming you have middleware that sets request.organization, 
        # or you get it from the user's profile.
        if hasattr(request, 'organization'):
            org = request.organization
        else:
            # Fallback logic if middleware isn't present
            org = request.user.organization if hasattr(request.user, 'organization') else None
        
        if not org:
            return Response({"detail": "No organization found for this user."}, status=status.HTTP_403_FORBIDDEN)

        # 4. Save/Update DB
        # The 'access_token' assignment here automatically triggers the 
        # encryption logic defined in the Integration model setter.
        config_data = {
            'username': gh_username, 
            'avatar_url': gh_user.get('avatar_url'),
            'scopes': token_data.get('scope', ''),
            'webhook_secret': token_data.get('webhook_secret', '')  # GitHub may return webhook secret
        }
        
        integration, created = Integration.objects.update_or_create(
            organization=org,
            provider='github',
            external_id=external_id,
            defaults={
                'name': f"GitHub ({gh_username})",
                'access_token': access_token, 
                # 'refresh_token': refresh_token, # Uncomment if your app supports rotation
                'config': config_data,
                'status': 'active'
            }
        )

        logger.info(f"Integration {'created' if created else 'updated'} for Org {org.id}")

        return Response({
            "status": "connected",
            "provider": "github",
            "account": gh_username,
            "integration_id": integration.id
        })


from drf_spectacular.utils import extend_schema

@extend_schema(auth=[], summary="GitHub Webhook Listener")
class GitHubWebhookView(APIView):
    """
    POST /api/webhooks/github/
    
    Receives GitHub webhook events and triggers audits.
    
    SECURITY:
    - Verifies X-Hub-Signature-256 to ensure authenticity
    - Uses organization's stored webhook secret
    - Only accepts 'push' events
    - Returns 200 OK immediately after queuing async task (no waiting)
    """
    permission_classes = [AllowAny]  # Webhooks don't have user context
    
    @method_decorator(ratelimit(key='ip', rate='100/m', method='POST', block=True))
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        """
        Handle GitHub webhook event.
        
        Expected headers:
        - X-Hub-Signature-256: sha256=<signature>
        - X-GitHub-Event: event type
        - X-GitHub-Delivery: delivery ID
        """
        try:
            # Get the signature from headers
            signature_header = request.headers.get('X-Hub-Signature-256', '')
            github_event = request.headers.get('X-GitHub-Event', '')
            
            if not signature_header:
                logger.warning("Webhook received without X-Hub-Signature-256")
                return Response(
                    {'error': 'Missing signature'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Get the raw body for signature verification
            # Must use request.body (raw bytes), not request.data (parsed JSON)
            body = request.body
            if isinstance(body, str):
                body = body.encode('utf-8')
            
            # Extract repository URL from payload
            repo_url = request.data.get('repository', {}).get('url', '')
            
            if not repo_url:
                logger.warning("Webhook received without repository URL")
                return Response(
                    {'error': 'Missing repository URL'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Find the integration by repository URL
            # Integration meta_data stores 'repo_name' like 'owner/repo'
            integrations = Integration.objects.filter(
                provider='github',
                meta_data__contains='repo'
            )
            
            matching_integration = None
            for integration in integrations:
                repo_name = integration.meta_data.get('repo_name', '')
                # Normalize URL comparison
                if repo_name and repo_name.lower() in repo_url.lower():
                    matching_integration = integration
                    break
            
            if not matching_integration:
                logger.warning(f"No integration found for webhook from {repo_url}")
                return Response(
                    {'error': 'Integration not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Verify webhook signature
            if not self._verify_signature(
                body,
                signature_header,
                matching_integration
            ):
                logger.warning(
                    f"Invalid webhook signature for integration {matching_integration.id}"
                )
                return Response(
                    {'error': 'Invalid signature'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Only process 'push' events
            if github_event != 'push':
                logger.debug(f"Ignoring webhook event: {github_event}")
                return Response(
                    {'message': f'Event {github_event} ignored'},
                    status=status.HTTP_200_OK
                )
            
            # Trigger async audit task
            # This returns immediately without waiting for the audit to complete
            from apps.audits.models import Audit
            
            org = matching_integration.organization
            if not org:
                logger.error(f"Integration {matching_integration.id} has no organization")
                return Response(
                    {'error': 'No organization'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Create audit (will be picked up by Celery)
            audit = Audit.objects.create(
                organization=org,
                triggered_by=None,  # Webhook-triggered, no user
                status='PENDING'
            )
            
            # Queue the audit task
            run_audit_task.delay(str(audit.id))
            
            logger.info(
                f"Webhook audit triggered for org {org.name}, repo {repo_url}, audit_id {audit.id}"
            )
            
            # Return 200 OK immediately
            return Response(
                {
                    'status': 'queued',
                    'message': 'Audit task queued',
                    'audit_id': str(audit.id)
                },
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.exception(f"Error processing webhook: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @staticmethod
    def _verify_signature(body: bytes, signature_header: str, integration) -> bool:
        """
        Verify GitHub webhook signature using HMAC-SHA256.
        
        Args:
            body: Raw request body (bytes)
            signature_header: X-Hub-Signature-256 header value (sha256=<hex>)
            integration: Integration object with webhook_secret
        
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Get webhook secret from integration metadata
            webhook_secret = integration.meta_data.get('webhook_secret')
            
            if not webhook_secret:
                logger.error(f"No webhook secret for integration {integration.id}")
                return False
            
            # Extract the hash from the header
            # Format: sha256=<hash>
            if not signature_header.startswith('sha256='):
                logger.error("Invalid signature header format")
                return False
            
            received_hash = signature_header[7:]  # Remove 'sha256=' prefix
            
            # Calculate the expected hash
            # Ensure webhook_secret is bytes
            if isinstance(webhook_secret, str):
                webhook_secret = webhook_secret.encode('utf-8')
            if isinstance(body, str):
                body = body.encode('utf-8')
            
            expected_hash = hmac.new(
                webhook_secret,
                body,
                hashlib.sha256
            ).hexdigest()
            
            # Compare using constant-time comparison to prevent timing attacks
            return hmac.compare_digest(received_hash, expected_hash)
        
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False
















