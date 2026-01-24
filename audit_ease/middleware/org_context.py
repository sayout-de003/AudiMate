import logging
import uuid
from django.http import JsonResponse
from django.utils.functional import SimpleLazyObject
from django.core.exceptions import ValidationError

# We import dynamically inside the method to avoid "AppRegistryNotReady" 
# errors during startup if models load before apps are ready.
from django.apps import apps

logger = logging.getLogger(__name__)

class OrgContextMiddleware:
    """
    Middleware to extract Organization ID from headers, validate access, 
    and set 'request.organization'.
    If no header provided, auto-selects the user's first organization.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Initialize request.organization as None by default
        request.organization = None

        # DEBUG: Print to confirm middleware is running
        if request.path.startswith('/api/v1/audits'):
            print(f"🔍 OrgContextMiddleware: User={request.user.is_authenticated}, Path={request.path}")

        # 2. Skip logic for unauthenticated users
        if not request.user.is_authenticated:
            return self.get_response(request)

        # 3. Import models
        Organization = apps.get_model('organizations', 'Organization')
        Membership = apps.get_model('organizations', 'Membership')

        # 4. Check for the Header
        org_id = request.headers.get("X-Organization-ID")

        if org_id:
            # Validate UUID format to prevent SQL/Database errors before fetching
            try:
                uuid.UUID(str(org_id))
            except ValueError:
                return JsonResponse(
                    {"detail": "Invalid Organization ID format."}, 
                    status=400
                )

            # Validate Membership and Fetch Organization
            try:
                # Efficiently check if the organization exists AND user is a member
                membership = Membership.objects.select_related('organization').get(
                    user=request.user,
                    organization__id=org_id
                )
                
                # Success: Attach the full organization object to the request
                request.organization = membership.organization
                
            except Membership.DoesNotExist:
                logger.warning(f"Unauthorized access attempt: User {request.user.id} tried accessing Org {org_id}")
                return JsonResponse(
                    {"detail": "Organization not found or you do not have access."}, 
                    status=403
                )
        else:
            # No header provided - auto-select the user's first organization
            try:
                membership = Membership.objects.select_related('organization').filter(
                    user=request.user
                ).first()
                
                if membership:
                    request.organization = membership.organization
                    logger.info(f"Auto-selected organization {membership.organization.id} ({membership.organization.name}) for user {request.user.id}")
                else:
                    logger.warning(f"No organization membership found for user {request.user.id}")
                # If no membership found, request.organization stays None
                # Endpoints can handle this by requiring organization context
                
            except Exception as e:
                logger.error(f"Error auto-selecting organization for user {request.user.id}: {e}")

        return self.get_response(request)