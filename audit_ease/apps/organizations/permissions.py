"""
Organization-Level Permission Classes

These permissions ensure strict data isolation between organizations.
Each organization can only access its own data.
"""

from rest_framework import permissions
from django.core.exceptions import PermissionDenied
from apps.organizations.models import Organization, Membership

class IsSameOrganization(permissions.BasePermission):
    """
    Custom permission to ensure a user can only access objects 
    belonging to their own organization.
    
    CRITICAL: This is the primary isolation mechanism that prevents
    Company A from seeing Company B's security audits and findings.
    
    Applied at class level: All HTTP methods must satisfy this permission.
    Applied at object level: Checks if the object belongs to user's org.
    """

    def has_permission(self, request, view):
        """
        Check that user belongs to at least one organization.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        # User must have at least one organization membership
        return Membership.objects.filter(user=request.user).exists()

    def has_object_permission(self, request, view, obj):
        """
        Check if the object belongs to the user's organization.
        
        This prevents:
        - Audit leakage between organizations
        - Unauthorized access to integration tokens
        - Cross-org evidence viewing
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if object has an 'organization' attribute
        # Check if object has an 'organization' attribute
        if hasattr(obj, 'organization'):
            target_org = obj.organization
        elif isinstance(obj, Organization):
            target_org = obj
        else:
            # Fallback for objects that might not be org-linked directly
            return False
        
        # CRITICAL FIX: User can have multiple memberships
        # Check if user has membership in the object's organization
        has_membership = Membership.objects.filter(
            user=request.user,
            organization=target_org
        ).exists()
        
        return has_membership


class IsOrgAdminOrReadOnly(permissions.BasePermission):
    """
    Permission that allows organization admins full access,
    while other members get read-only access.
    
    Supports RBAC: ADMIN vs MEMBER vs VIEWER roles.
    CRITICAL: Handles users with multiple organization memberships.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Safe methods allowed for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Non-safe methods require admin role in any organization
        # CRITICAL FIX: Use filter().exists() for multiple memberships
        has_admin_role = Membership.objects.filter(
            user=request.user,
            role=Membership.ROLE_ADMIN
        ).exists()
        return has_admin_role


class IsOrgAdmin(permissions.BasePermission):
    """
    Permission that only allows organization admins of the SPECIFIC organization.
    Checks `org_id` kwarg in the view.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Get org_id from view kwargs
        org_id = view.kwargs.get('org_id') or view.kwargs.get('pk')
        if not org_id:
            # If no org_id in URL, maybe check if user is admin of ANY org?
            # Or deny? For strict security, if this permission is used, it expects an org context.
            # But let's fallback to "admin of ANY org" if strictly necessary, OR strict deny.
            # Requirement says: "ensure only users with the role ADMIN within the target organization".
            # So if no target org, we can't verify.
            
            # Use case: List all my organizations? -> That might use a different permission.
            # Use case: /orgs/{org_id}/admin/... -> Has org_id.
            
            return False

        # Check membership with Admin role for this specific org
        return Membership.objects.filter(
            user=request.user,
            organization_id=org_id,
            role=Membership.ROLE_ADMIN
        ).exists()


class CanRunAudits(permissions.BasePermission):
    """
    Permission to allow users with MEMBER or ADMIN role to run audits.
    VIEWER role cannot initiate audits (read-only access only).
    CRITICAL: Handles users with multiple organization memberships.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # CRITICAL FIX: Use filter().exists() for multiple memberships
        # Check if user has ADMIN or MEMBER role in any organization
        can_run = Membership.objects.filter(
            user=request.user,
            role__in=[Membership.ROLE_ADMIN, Membership.ROLE_MEMBER]
        ).exists()
        return can_run


class HasActiveSubscription(permissions.BasePermission):
    """
    Permission to restrict access to premium features based on subscription status.
    
    Checks if the user's organization has an active subscription.
    Used to gate premium endpoints like CSV export, PDF reports, etc.
    
    SECURITY: Only allows 'active' subscription status.
    Grace periods and trial periods can be added in the future.
    
    Usage:
    @permission_classes([IsAuthenticated, HasActiveSubscription])
    def some_premium_feature(request):
        ...
    
    Error Response (403):
    {
        "detail": "Upgrade to Premium to access this feature"
    }
    """
    
    def has_permission(self, request, view):
        """
        Check if the user's organization has an active subscription.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get user's organization(s)
        # For multi-org users, check if they have an active subscription in ANY org
        membership = Membership.objects.filter(
            user=request.user,
            organization__subscription_status=Organization.SUBSCRIPTION_STATUS_ACTIVE
        ).first()
        
        if membership:
            # Store the organization in request for use in views
            request.user_organization = membership.organization
            return True
        
        # Could extend this to support trial periods or grace periods
        # membership = Membership.objects.filter(user=request.user).first()
        # if membership and membership.organization.is_in_trial():
        #     return True
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """
        Optionally verify object belongs to an org with active subscription.
        """
        if not hasattr(obj, 'organization'):
            return False
        
        is_active = (
            obj.organization.subscription_status 
            == Organization.SUBSCRIPTION_STATUS_ACTIVE
        )
        
        # Also verify user has membership
        has_membership = Membership.objects.filter(
            user=request.user,
            organization=obj.organization
        ).exists()
        
        return is_active and has_membership
