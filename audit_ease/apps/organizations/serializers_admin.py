
from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization, Membership, OrganizationInvite, ActivityLog

User = get_user_model()

class OrgDashboardStatsSerializer(serializers.Serializer):
    """
    Serializer for the high-level dashboard statistics.
    """
    total_members = serializers.IntegerField()
    active_seats = serializers.IntegerField()
    recent_activity_count = serializers.IntegerField()
    # Add other stats as needed, e.g., total_audits, finding_count etc.
    # total_audits = serializers.IntegerField()


class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'is_active']


class OrgMemberSerializer(serializers.ModelSerializer):
    """
    Serializer for listing members with their roles.
    Includes User details.
    """
    user = UserSimpleSerializer(read_only=True)
    joined_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = Membership
        fields = ['id', 'user', 'role', 'joined_at', 'updated_at']
        read_only_fields = ['id', 'user', 'organization', 'joined_at', 'updated_at']


class InviteSerializer(serializers.ModelSerializer):
    """
    Serializer for pending invites.
    """
    invited_by_email = serializers.EmailField(source='invited_by.email', read_only=True)
    
    class Meta:
        model = OrganizationInvite
        fields = ['id', 'email', 'role', 'status', 'created_at', 'expires_at', 'invited_by_email']
        read_only_fields = ['id', 'status', 'created_at', 'expires_at', 'token', 'invited_by_email']


class ActivityLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source='actor.email', read_only=True)
    
    class Meta:
        model = ActivityLog
        fields = ['id', 'actor', 'actor_email', 'action', 'metadata', 'created_at']
        read_only_fields = ['id', 'actor', 'actor_email', 'organization', 'created_at']


class OrgSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for updating Organization settings (Name, Logo).
    """
    class Meta:
        model = Organization
        fields = ['id', 'name', 'slug', 'subscription_status'] # Add logo field when available
        read_only_fields = ['id', 'slug', 'subscription_status'] 
        # Note: slug is read-only usually, or handled carefully.
        # subscription_status is read-only here.

