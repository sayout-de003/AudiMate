"""
Organization API Serializers

Industry-Grade Features:
- Nested serializers for related data
- Comprehensive validation with custom validators
- Read-only fields for sensitive data
- Contextual field inclusion
- Proper error messaging
"""

from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from .models import Organization, Membership, OrganizationInvite
from apps.users.models import User


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user info for responses (no sensitive data)."""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name']
        read_only_fields = ['id', 'email']

    def get_full_name(self, obj) -> str:
        """Construct full name from name fields."""
        name_parts = [obj.first_name, obj.middle_name, obj.last_name]
        return ' '.join([part for part in name_parts if part]).strip() or obj.email


class MembershipSerializer(serializers.ModelSerializer):
    """Membership with embedded user data."""
    user = UserBasicSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        write_only=True,
        required=False
    )
    can_invite_members = serializers.SerializerMethodField()
    can_manage_members = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = [
            'id',
            'user',
            'user_id',
            'role',
            'joined_at',
            'can_invite_members',
            'can_manage_members',
        ]
        read_only_fields = ['id', 'user', 'joined_at']

    def get_can_invite_members(self, obj) -> bool:
        """Determine if this member can invite others."""
        return obj.can_invite_members()

    def get_can_manage_members(self, obj) -> bool:
        """Determine if this member can manage others."""
        return obj.can_manage_members()


class OrganizationSerializer(serializers.ModelSerializer):
    """
    Organization serializer for list/create views.
    Minimal representation with member count.
    """
    owner = UserBasicSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    admin_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'id',
            'name',
            'slug',
            'owner',
            'member_count',
            'admin_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'owner', 'created_at', 'updated_at']

    def get_member_count(self, obj) -> int:
        """Get total member count."""
        return obj.members.count()

    def get_admin_count(self, obj) -> int:
        """Get admin member count."""
        return obj.get_admin_members().count()

    def validate_name(self, value: str) -> str:
        """Validate organization name."""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Organization name cannot be empty.")
        if len(value) > 255:
            raise serializers.ValidationError(
                "Organization name cannot exceed 255 characters."
            )
        return value.strip()

    def create(self, validated_data):
        """
        Create organization and auto-create ADMIN membership for creator.
        
        Uses transaction to ensure atomicity.
        """
        user = self.context['request'].user
        
        with transaction.atomic():
            # Create organization with user as owner
            organization = Organization.objects.create(
                owner=user,
                **validated_data
            )
            
            # Auto-create admin membership for creator
            Membership.objects.create(
                user=user,
                organization=organization,
                role=Membership.ROLE_ADMIN
            )
        
        return organization


class OrganizationDetailSerializer(serializers.ModelSerializer):
    """
    Detailed organization serializer with full member list.
    Used for retrieve/update views.
    """
    owner = UserBasicSerializer(read_only=True)
    members = MembershipSerializer(read_only=True, many=True)
    member_count = serializers.SerializerMethodField()
    admin_count = serializers.SerializerMethodField()
    pending_invites_count = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'id',
            'name',
            'slug',
            'owner',
            'members',
            'member_count',
            'admin_count',
            'pending_invites_count',
            'is_owner',
            'is_admin',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'slug',
            'owner',
            'members',
            'created_at',
            'updated_at',
        ]

    def get_member_count(self, obj) -> int:
        """Get total member count."""
        return obj.members.count()

    def get_admin_count(self, obj) -> int:
        """Get admin member count."""
        return obj.get_admin_members().count()

    def get_pending_invites_count(self, obj) -> int:
        """Get pending invites count."""
        return obj.invites.filter(
            status=OrganizationInvite.STATUS_PENDING
        ).count()

    def get_is_owner(self, obj) -> bool:
        """Check if current user is organization owner."""
        user = self.context['request'].user
        return obj.owner == user

    def get_is_admin(self, obj) -> bool:
        """Check if current user is admin."""
        user = self.context['request'].user
        membership = obj.members.filter(user=user).first()
        return membership.is_admin() if membership else False

    def validate_name(self, value: str) -> str:
        """Validate organization name."""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Organization name cannot be empty.")
        if len(value) > 255:
            raise serializers.ValidationError(
                "Organization name cannot exceed 255 characters."
            )
        return value.strip()


class OrganizationInviteSerializer(serializers.ModelSerializer):
    """
    Serializer for creating invites.
    Used by ADMIN to invite new members.
    """
    invited_by = UserBasicSerializer(read_only=True)
    accepted_by = UserBasicSerializer(read_only=True)

    class Meta:
        model = OrganizationInvite
        fields = [
            'id',
            'email',
            'role',
            'status',
            'invited_by',
            'accepted_by',
            'created_at',
            'expires_at',
            'used_at',
        ]
        read_only_fields = [
            'id',
            'status',
            'invited_by',
            'accepted_by',
            'created_at',
            'expires_at',
            'used_at',
        ]

    def validate_email(self, value: str) -> str:
        """Validate email address."""
        # Normalize email
        value = value.lower().strip()
        
        if not value:
            raise serializers.ValidationError("Email cannot be empty.")
        
        # Basic email validation
        if '@' not in value:
            raise serializers.ValidationError("Please provide a valid email address.")
        
        return value

    def validate(self, data):
        """Cross-field validation."""
        email = data.get('email')
        organization = self.context.get('organization')
        
        if not organization:
            raise serializers.ValidationError("Organization is required in context.")
        
        # Check if user is already a member
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            if organization.members.filter(user=user).exists():
                raise serializers.ValidationError(
                    {'email': f'{email} is already a member of this organization.'}
                )
        
        # Check if user is organization owner
        if organization.owner.email == email:
            raise serializers.ValidationError({
                'email': 'Cannot invite the organization owner.'
            })
        
        # Check for existing pending invite
        existing_invite = OrganizationInvite.objects.filter(
            organization=organization,
            email=email,
            status=OrganizationInvite.STATUS_PENDING
        ).first()
        
        if existing_invite and not existing_invite.is_expired():
            raise serializers.ValidationError({
                'email': f'This email has already been invited. Invite expires at '
                        f'{existing_invite.expires_at.isoformat()}'
            })
        
        # Mark expired invites
        if existing_invite and existing_invite.is_expired():
            existing_invite.mark_expired()
        
        return data

    def create(self, validated_data):
        """Create invite with organization and invited_by from context."""
        organization = self.context['organization']
        request_user = self.context['request'].user
        
        invite = OrganizationInvite.objects.create(
            organization=organization,
            invited_by=request_user,
            **validated_data
        )
        
        return invite


class InviteAcceptSerializer(serializers.Serializer):
    """
    Serializer for accepting an invite.
    User provides the token received in email.
    """
    token = serializers.CharField(
        max_length=64,
        min_length=64,
        required=True,
        help_text="The 64-character token from the invitation email"
    )

    def validate_token(self, value: str) -> str:
        """Validate that token exists and is valid."""
        try:
            invite = OrganizationInvite.objects.get(token=value)
        except OrganizationInvite.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired invitation token.")
        
        # Check if invite is still valid
        if not invite.is_valid():
            if invite.is_expired():
                raise serializers.ValidationError(
                    "This invitation has expired. Please contact your organization admin."
                )
            else:
                raise serializers.ValidationError(
                    "This invitation is no longer valid."
                )
        
        return value

    def validate(self, data):
        """Final validation and invite lookup."""
        token = data.get('token')
        
        try:
            invite = OrganizationInvite.objects.get(token=token)
            data['invite'] = invite
        except OrganizationInvite.DoesNotExist:
            raise serializers.ValidationError("Invalid invitation token.")
        
        return data

    def save(self):
        """Accept the invite and create membership."""
        invite = self.validated_data['invite']
        user = self.context['request'].user
        
        # Validate invite
        if not invite.is_valid():
            raise serializers.ValidationError("This invitation is no longer valid.")
        
        # Accept the invite (this handles membership creation)
        try:
            membership = invite.accept(user)
            return membership
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))

    def to_representation(self, instance):
        """Return membership data after accept."""
        return MembershipSerializer(instance, context=self.context).data


class OrganizationInviteListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing invites (for admins).
    Includes invitation details but not sensitive info.
    """
    invited_by = UserBasicSerializer(read_only=True)

    class Meta:
        model = OrganizationInvite
        fields = [
            'id',
            'email',
            'role',
            'status',
            'invited_by',
            'created_at',
            'expires_at',
        ]
        read_only_fields = fields
