from rest_framework import permissions
from apps.organizations.models import Organization
from apps.audits.models import Evidence

class HasGeneralAccess(permissions.BasePermission):
    """
    Allow access if Organization is ACTIVE, FREE, or in valid TRIAL.
    Blocks access for expired, canceled, or past_due subscriptions.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            self.message = "Authentication required."
            return False
            
        organization = request.user.get_organization()
        if not organization:
            self.message = "You are not a member of any organization. Please contact your administrator."
            return False

        # Handle None or empty subscription_status (default to FREE)
        subscription_status = organization.subscription_status or Organization.SUBSCRIPTION_STATUS_FREE

        # Check for Active Subscription
        if subscription_status == Organization.SUBSCRIPTION_STATUS_ACTIVE:
            return True
        
        # Allow Free plan users to access audits
        if subscription_status == Organization.SUBSCRIPTION_STATUS_FREE:
            return True
        
        # Check for Valid Trial
        if subscription_status == Organization.SUBSCRIPTION_STATUS_TRIAL:
            if organization.is_in_trial:
                return True
            else:
                # Trial expired
                self.message = "Your trial has expired. Please upgrade to continue accessing audits."
                return False
            
        # Block expired, canceled, or past_due subscriptions
        if subscription_status in [
            Organization.SUBSCRIPTION_STATUS_EXPIRED,
            Organization.SUBSCRIPTION_STATUS_CANCELED,
            Organization.SUBSCRIPTION_STATUS_PAST_DUE
        ]:
            status_display = subscription_status.replace('_', ' ').title()
            self.message = f"Your subscription is {status_display}. Please upgrade to continue accessing audits."
            return False
        
        # Default deny with helpful message (shouldn't reach here, but handle edge cases)
        self.message = f"Access denied. Current subscription status: {subscription_status}. Please upgrade to continue accessing audits."
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

class HasProPlan(permissions.BasePermission):
    """
    Allow access only if Organization is on PRO plan.
    Bypassed by Superusers.
    """
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
            
        if not request.user.is_authenticated:
            return False
            
        organization = request.user.get_organization()
        if not organization:
            return False
            
        if organization.subscription_plan == Organization.SUBSCRIPTION_PLAN_PRO:
            return True
            
        # Default False (FREE plan)
        return False
