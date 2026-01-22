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
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Initialize request.organization as None by default
        request.organization = None

        # 2. Skip logic for unauthenticated users (unless you have public org pages)
        if not request.user.is_authenticated:
            return self.get_response(request)

        # 3. Check for the Header
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

            # 4. Validate Membership and Fetch Organization
            # We use apps.get_model to avoid circular import issues at module level
            Organization = apps.get_model('organizations', 'Organization')
            Membership = apps.get_model('organizations', 'Membership')

            try:
                # Efficiently check if the organization exists AND user is a member
                # This query assumes you have a Membership model linking User and Organization
                membership = Membership.objects.select_related('organization').get(
                    user=request.user,
                    organization__id=org_id
                )
                
                # Success: Attach the full organization object to the request
                request.organization = membership.organization
                
            except Membership.DoesNotExist:
                # Differentiate between "Org doesn't exist" and "User not a member" 
                # strictly for logging, but return a generic 403/404 to the user for security.
                logger.warning(f"Unauthorized access attempt: User {request.user.id} tried accessing Org {org_id}")
                return JsonResponse(
                    {"detail": "Organization not found or you do not have access."}, 
                    status=403
                )

        return self.get_response(request)