from rest_framework import permissions
from apps.organizations.models import Organization

class HasActiveSubscription(permissions.BasePermission):
    """
    Allows access only to users whose organization has an active subscription.
    """
    message = "Upgrade to Premium to export reports."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        organization = request.user.get_organization()
        if not organization:
            return False
            
        return organization.subscription_status == Organization.SUBSCRIPTION_STATUS_ACTIVE
