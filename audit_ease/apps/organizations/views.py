"""
Organization Management API Views

Industry-Grade Features:
- Comprehensive permission checks (authentication, authorization, org isolation)
- RESTful ViewSets with proper HTTP semantics
- Custom action endpoints for invites and member management
- Detailed error responses with context
- Audit logging for sensitive operations
- Transaction atomicity where needed
- Filtering and pagination
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.cache import cache_page
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from auditlog.models import LogEntry
import logging

from .models import Organization, Membership, OrganizationInvite
from .serializers import (
    OrganizationSerializer,
    OrganizationDetailSerializer,
    MembershipSerializer,
    OrganizationInviteSerializer,
    InviteAcceptSerializer,
    OrganizationInviteListSerializer,
)
from .permissions import IsSameOrganization, IsOrgAdmin
from apps.users.models import User

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for list endpoints."""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    Organization CRUD API Endpoint
    
    GET    /api/v1/organizations/           - List user's organizations
    POST   /api/v1/organizations/           - Create new organization
    GET    /api/v1/organizations/{id}/      - Get organization details
    PUT    /api/v1/organizations/{id}/      - Update organization (ADMIN only)
    PATCH  /api/v1/organizations/{id}/      - Partial update (ADMIN only)
    DELETE /api/v1/organizations/{id}/      - Delete organization (ADMIN only)
    
    Industry-Grade Security:
    - IsAuthenticated: User must be logged in
    - IsSameOrganization: User can only access their own org
    - IsOrgAdmin: Modify operations require ADMIN role
    """
    
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [
        permissions.IsAuthenticated,
        IsSameOrganization,
    ]

    def get_serializer_class(self):
        """Return detailed serializer for retrieve, update actions."""
        if self.action in ['retrieve', 'update', 'partial_update']:
            return OrganizationDetailSerializer
        return OrganizationSerializer

    def get_queryset(self):
        """
        Filter organizations to only those user belongs to.
        
        CRITICAL SECURITY: Prevents users from listing other orgs.
        """
        user = self.request.user
        return Organization.objects.filter(
            members__user=user
        ).distinct().prefetch_related('members__user', 'owner')

    def perform_create(self, serializer):
        """
        Create organization.
        
        AUTOMATIC: User becomes ADMIN automatically.
        """
        logger.info(f"Creating new organization for user {self.request.user.email}")
        serializer.save()

    def perform_update(self, serializer):
        """
        Update organization (ADMIN only).
        
        ENFORCED: Only ADMIN members can update.
        """
        org = self.get_object()
        user = self.request.user
        
        # Check if user is admin
        membership = org.members.filter(user=user).first()
        if not membership or not membership.is_admin():
            raise PermissionDenied(
                "Only organization admins can update organization settings."
            )
        
        logger.info(
            f"Organization {org.id} updated by {user.email} - "
            f"Changes: {serializer.validated_data}"
        )
        serializer.save()

    def perform_destroy(self, instance):
        """
        Delete organization (ADMIN only).
        
        ENFORCED: Only ADMIN members can delete.
        RESTRICTIONS:
        - Cascades all related data (audits, invites, etc.)
        - Logs the deletion
        """
        user = self.request.user
        org = instance
        
        # Check if user is admin
        membership = org.members.filter(user=user).first()
        if not membership or not membership.is_admin():
            raise PermissionDenied(
                "Only organization admins can delete the organization."
            )
        
        logger.warning(
            f"Organization {org.id} ({org.name}) DELETED by {user.email}"
        )
        instance.delete()

    @action(detail=True, methods=['post'], permission_classes=[
        permissions.IsAuthenticated, IsSameOrganization, IsOrgAdmin
    ])
    def invite_member(self, request, pk=None):
        """
        POST /api/v1/organizations/{id}/invite_member/
        
        Invite a new member to the organization.
        
        Request Body:
        {
            "email": "newmember@example.com",
            "role": "MEMBER"  # ADMIN, MEMBER, or VIEWER
        }
        
        Returns:
        {
            "id": "...",
            "email": "newmember@example.com",
            "role": "MEMBER",
            "status": "PENDING",
            "expires_at": "2026-01-27T...",
            ...
        }
        
        SECURITY:
        - Only ADMIN members can send invites
        - IsSameOrganization ensures org isolation
        - Validates email and role
        - Prevents duplicate invites
        - Prevents inviting existing members
        """
        org = self.get_object()
        user = request.user
        
        # Verify user is admin (extra check beyond permissions)
        membership = org.members.filter(user=user).first()
        if not membership or not membership.is_admin():
            raise PermissionDenied("Only admins can invite members.")
        
        # Create serializer with org context
        serializer = OrganizationInviteSerializer(
            data=request.data,
            context={
                'request': request,
                'organization': org,
            }
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        invite = serializer.save()
        
        # Log invitation
        logger.info(
            f"Invitation sent to {invite.email} for org {org.name} "
            f"by {user.email} with role {invite.role}"
        )
        
        # TODO: Send email notification to invite.email with token
        # For now, just log
        logger.debug(f"[MOCK] Email sent to {invite.email}. Token: {invite.token}")
        
        return Response(
            OrganizationInviteSerializer(invite).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'], permission_classes=[
        permissions.IsAuthenticated, IsSameOrganization, IsOrgAdmin
    ])
    def invites(self, request, pk=None):
        """
        GET /api/v1/organizations/{id}/invites/
        
        List all pending and accepted invites for this organization.
        
        SECURITY: Only ADMIN members can view invites.
        """
        org = self.get_object()
        
        # Get all invites for organization
        invites = org.invites.select_related('invited_by', 'accepted_by')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            invites = invites.filter(status=status_filter)
        
        page = self.paginate_queryset(invites)
        if page is not None:
            serializer = OrganizationInviteListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = OrganizationInviteListSerializer(invites, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[
        permissions.IsAuthenticated, IsSameOrganization, IsOrgAdmin
    ])
    def members(self, request, pk=None):
        """
        GET /api/v1/organizations/{id}/members/
        
        List all members of the organization.
        
        SECURITY: All authenticated members can view members list.
        """
        org = self.get_object()
        members = org.members.select_related('user')
        
        # Filter by role if provided
        role_filter = request.query_params.get('role')
        if role_filter:
            members = members.filter(role=role_filter)
        
        page = self.paginate_queryset(members)
        if page is not None:
            serializer = MembershipSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = MembershipSerializer(members, many=True)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['delete'],
        permission_classes=[permissions.IsAuthenticated, IsSameOrganization, IsOrgAdmin],
        url_path='members/(?P<user_id>[^/.]+)'
    )
    def remove_member(self, request, pk=None, user_id=None):
        """
        DELETE /api/v1/organizations/{id}/members/{user_id}/
        
        Remove a member from the organization.
        
        SECURITY:
        - Only ADMIN members can remove members
        - Cannot remove organization owner
        - Cannot remove last admin
        
        Returns:
        {
            "detail": "Member successfully removed"
        }
        """
        org = self.get_object()
        user = self.request.user
        
        # Verify requesting user is admin
        requester_membership = org.members.filter(user=user).first()
        if not requester_membership or not requester_membership.is_admin():
            raise PermissionDenied("Only admins can remove members.")
        
        # Get the user to remove
        try:
            user_to_remove = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise NotFound("User not found.")
        
        # Prevent removing organization owner
        if org.owner == user_to_remove:
            raise ValidationError(
                "Cannot remove the organization owner. Transfer ownership first."
            )
        
        # Prevent removing yourself
        if user == user_to_remove:
            raise ValidationError("You cannot remove yourself from the organization.")
        
        # Get the membership to remove
        membership = org.members.filter(user=user_to_remove).first()
        if not membership:
            raise NotFound(
                f"User {user_to_remove.email} is not a member of this organization."
            )
        
        # Prevent removing last admin
        admin_count = org.get_admin_members().count()
        if membership.is_admin() and admin_count == 1:
            raise ValidationError(
                "Cannot remove the last admin member. "
                "Assign another admin before removing this one."
            )
        
        # Remove membership
        logger.info(
            f"Member {user_to_remove.email} removed from {org.name} "
            f"by {user.email}"
        )
        membership.delete()
        
        return Response(
            {'detail': f'Member {user_to_remove.email} successfully removed'},
            status=status.HTTP_204_NO_CONTENT
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def accept_invite(request):
    """
    POST /api/v1/invites/accept/
    
    Accept an organization invitation using the token.
    
    This endpoint is "global" (not org-specific) because the user
    doesn't belong to the org yet - they're using the token to join.
    
    Request Body:
    {
        "token": "64_character_hex_string_from_email"
    }
    
    Returns:
    {
        "id": "membership_id",
        "user": {...},
        "role": "MEMBER",
        "joined_at": "...",
        "can_invite_members": false,
        "can_manage_members": false
    }
    
    SECURITY:
    - User must be authenticated
    - Token must be valid and not expired
    - User cannot already be a member
    - Prevents re-using tokens
    """
    user = request.user
    
    serializer = InviteAcceptSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        membership = serializer.save()
        
        logger.info(
            f"User {user.email} accepted invitation to organization "
            f"{membership.organization.name} with role {membership.role}"
        )
        
        return Response(
            MembershipSerializer(membership, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        logger.exception(f"Error accepting invite: {e}")
        return Response(
            {'detail': 'Failed to accept invitation. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_organizations(request):
    """
    GET /api/v1/user-organizations/
    
    Get all organizations the user belongs to.
    Returns a list of organizations with member details.
    
    Query Parameters:
    - role: Filter by membership role (ADMIN, MEMBER, VIEWER)
    - page_size: Results per page (default 25, max 100)
    - page: Page number (default 1)
    """
    user = request.user
    
    # Get all organizations user is a member of
    memberships = Membership.objects.filter(user=user).select_related(
        'organization',
        'organization__owner'
    ).prefetch_related('organization__members__user')
    
    # Filter by role if provided
    role_filter = request.query_params.get('role')
    if role_filter:
        memberships = memberships.filter(role=role_filter)
    
    organizations = [m.organization for m in memberships]
    
    # Paginate
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(organizations, request)
    
    if page is not None:
        serializer = OrganizationDetailSerializer(
            page,
            many=True,
            context={'request': request}
        )
        return paginator.get_paginated_response(serializer.data)
    
    serializer = OrganizationDetailSerializer(
        organizations,
        many=True,
        context={'request': request}
    )
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_invite_validity(request):
    """
    GET /api/v1/invites/check/
    
    Check if an invitation token is valid.
    Used by frontend to show expiry, organization, role before accepting.
    
    Query Parameters:
    - token: The invitation token
    
    Returns:
    {
        "valid": true,
        "organization": "...",
        "role": "MEMBER",
        "expires_at": "...",
        "message": "..."
    }
    
    OR
    
    {
        "valid": false,
        "reason": "expired|invalid|already_member"
    }
    """
    token = request.query_params.get('token')
    
    if not token:
        return Response(
            {'detail': 'Token parameter is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        invite = OrganizationInvite.objects.select_related(
            'organization'
        ).get(token=token)
    except OrganizationInvite.DoesNotExist:
        return Response({
            'valid': False,
            'reason': 'invalid'
        })
    
    # Check if already a member
    if invite.organization.members.filter(user=request.user).exists():
        return Response({
            'valid': False,
            'reason': 'already_member',
            'message': 'You are already a member of this organization.'
        })
    
    # Check if valid
    if not invite.is_valid():
        if invite.is_expired():
            return Response({
                'valid': False,
                'reason': 'expired',
                'message': f'This invitation expired on {invite.expires_at.isoformat()}'
            })
        else:
            return Response({
                'valid': False,
                'reason': 'invalid'
            })
    
    # Valid
    from .serializers import OrganizationSerializer
    return Response({
        'valid': True,
        'organization': OrganizationSerializer(invite.organization).data,
        'role': invite.role,
        'expires_at': invite.expires_at.isoformat(),
    })


class ActivityLogView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    View for Customer Admins to see audit logs for their organization.
    
    Security:
    - Login Required
    - Must be Admin of the Organization
    - Scoped to only show logs from actors in the same organization
    """
    model = LogEntry
    template_name = 'settings/activity_log.html'
    context_object_name = 'logs'
    paginate_by = 25
    
    def test_func(self):
        """Verify user is an Admin of their organization."""
        org = self.request.user.get_organization()
        if not org:
            return False
            
        membership = Membership.objects.filter(
            user=self.request.user, 
            organization=org
        ).first()
        
        return membership and membership.is_admin()
        
    def get_queryset(self):
        """
        Filter logs to show only actions by members of the same organization.
        """
        user = self.request.user
        org = user.get_organization()
        
        if not org:
            return LogEntry.objects.none()
            
        # We want to see what employees (members) of this org did.
        # So we filter LogEntries where the actor is in this org.
        qs = LogEntry.objects.filter(
            actor__memberships__organization=org
        ).select_related('actor', 'content_type').order_by('-timestamp')
        
        return qs