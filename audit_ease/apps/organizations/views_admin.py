
from rest_framework import viewsets, generics, status, views
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q

from apps.organizations.models import Organization, Membership, OrganizationInvite, ActivityLog
from apps.organizations.serializers_admin import (
    OrgDashboardStatsSerializer,
    OrgMemberSerializer,
    InviteSerializer,
    ActivityLogSerializer,
    OrgSettingsSerializer
)
from apps.organizations.permissions import IsOrgAdmin

class BaseOrgAdminView:
    permission_classes = [IsOrgAdmin]
    
    def get_queryset(self):
        # Ensure we only return objects for the existing organization
        # and verify permissions handled by IsOrgAdmin
        return super().get_queryset()

    def get_organization(self):
        org_id = self.kwargs.get('org_id')
        return get_object_or_404(Organization, id=org_id)


class AdminDashboardView(BaseOrgAdminView, views.APIView):
    """
    GET /api/v1/orgs/{org_id}/admin/dashboard/
    Return high-level stats.
    """
    def get(self, request, org_id):
        organization = self.get_organization()
        
        # Calculate stats
        total_members = organization.members.count()
        # Active seats could be filtered by role or status if applicable
        active_seats = organization.members.filter(user__is_active=True).count()
        recent_activity_count = organization.activity_logs.filter(
            created_at__gte=organization.created_at  # placeholder for specific time window
        ).count()
        
        data = {
            "total_members": total_members,
            "active_seats": active_seats,
            "recent_activity_count": recent_activity_count
        }
        
        serializer = OrgDashboardStatsSerializer(data)
        return Response(serializer.data)


class MemberViewSet(viewsets.ModelViewSet):
    """
    GET /members/ - List members
    DELETE /members/{id}/ - Remove member
    """
    serializer_class = OrgMemberSerializer
    permission_classes = [IsOrgAdmin]

    def get_queryset(self):
        org_id = self.kwargs.get('org_id')
        return Membership.objects.filter(organization_id=org_id).select_related('user')

    def perform_destroy(self, instance):
        # Prevent deleting the last admin
        organization = instance.organization
        if instance.role == Membership.ROLE_ADMIN:
            admin_count = Membership.objects.filter(
                organization=organization, 
                role=Membership.ROLE_ADMIN
            ).count()
            if admin_count <= 1:
                raise ValidationError("Cannot remove the last administrator of the organization.")
        
        # Log the action
        ActivityLog.objects.create(
            organization=organization,
            actor=self.request.user,
            action="Removed Member",
            target=instance, # Generic relation if setup, else just string
            metadata={"removed_user_email": instance.user.email}
        )
        
        instance.delete()


class InviteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Manage Invites.
    POST /resend/ - Resend invite
    """
    serializer_class = InviteSerializer
    permission_classes = [IsOrgAdmin]
    
    def get_queryset(self):
        org_id = self.kwargs.get('org_id')
        return OrganizationInvite.objects.filter(organization_id=org_id)

    @action(detail=True, methods=['post'])
    def resend(self, request, org_id=None, pk=None):
        invite = self.get_object()
        
        if not invite.is_valid():
            return Response(
                {"error": "Invite is expired or already accepted."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # TODO: Trigger email resend task here
        # send_invite_email.delay(invite.id)
        
        # Log action
        ActivityLog.objects.create(
            organization=invite.organization,
            actor=request.user,
            action="Resent Invite",
            target=invite,
            metadata={"email": invite.email}
        )

        return Response({"status": "Invite resent successfully."})


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /logs/ - List audit logs
    """
    serializer_class = ActivityLogSerializer
    permission_classes = [IsOrgAdmin]

    def get_queryset(self):
        org_id = self.kwargs.get('org_id')
        return ActivityLog.objects.filter(organization_id=org_id).select_related('actor')


class OrgSettingsView(generics.RetrieveUpdateAPIView):
    """
    PATCH /settings/ - Update Org settings
    """
    serializer_class = OrgSettingsSerializer
    permission_classes = [IsOrgAdmin]
    
    def get_object(self):
        org_id = self.kwargs.get('org_id')
        return get_object_or_404(Organization, id=org_id)

    def perform_update(self, serializer):
        instance = serializer.save()
        
        # Log action
        ActivityLog.objects.create(
            organization=instance,
            actor=self.request.user,
            action="Updated Settings",
            target=instance,
            metadata={"changes": serializer.validated_data}
        )
