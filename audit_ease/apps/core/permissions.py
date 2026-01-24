from rest_framework import permissions
from apps.organizations.models import Organization
from apps.audits.models import Evidence

class HasGeneralAccess(permissions.BasePermission):
    """
    Allow access if Organization is ACTIVE or in valid TRIAL.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
            
        organization = request.user.get_organization()
        if not organization:
            return False

        # Check for Active Subscription
        if organization.subscription_status == Organization.SUBSCRIPTION_STATUS_ACTIVE:
            return True
        
        # Check for Valid Trial
        if organization.is_in_trial:
            return True
            
        # Optional: check if status is specifically TRIAL but expired vs just EXPIRED/CANCELLED
        # But per requirements: Allow logic if Active OR Trial.
        # If neither, deny.
        
        self.message = "Your trial has expired. Please upgrade to continue."
        return False

class HasPremiumFeatureAccess(permissions.BasePermission):
    """
    Allow access ONLY if subscription_status is ACTIVE.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
            
        organization = request.user.get_organization()
        if not organization:
            return False
            
        if organization.subscription_status == Organization.SUBSCRIPTION_STATUS_ACTIVE:
            return True
            
        # Allow Trial Access as well
        if organization.is_in_trial:
            return True
            
        self.message = "Exporting reports is a Premium feature. Upgrade to unlock."
        return False

class CheckTrialQuota(permissions.BasePermission):
    """
    For Creation Endpoints:
    If User is in TRIAL, check if Evidence count >= 50.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
            
        organization = request.user.get_organization()
        if not organization:
            return False
            
        # If Active, no quota
        if organization.subscription_status == Organization.SUBSCRIPTION_STATUS_ACTIVE:
            return True
            
        # If Trial (or anything else restrictive), check quota
        # Requirement says "If the user is in TRIAL mode"
        # We should probably enforce this for Free/Trial statuses
        if organization.subscription_status != Organization.SUBSCRIPTION_STATUS_ACTIVE:
            count = Evidence.objects.filter(audit__organization=organization).count()
            if count >= 50:
                self.message = "Trial limit reached (50 items). Upgrade for unlimited storage."
                return False
                
        return True
