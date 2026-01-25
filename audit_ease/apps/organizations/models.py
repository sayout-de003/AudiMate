import uuid
import secrets
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class Organization(models.Model):
    """
    The tenant container. All Audit data belongs to an Organization.
    
    Features:
    - Multi-tenant isolation via UUID primary key
    - Slug for readable URLs (unique)
    - Owner tracks who created the organization
    - Automatic timestamp tracking
    - Subscription billing status with Stripe integration
    """
    
    # Subscription status choices
    SUBSCRIPTION_STATUS_FREE = 'free'
    SUBSCRIPTION_STATUS_PRO = 'pro'  # Added for plan, though this is status, plan is separate
    
    SUBSCRIPTION_STATUS_TRIAL = 'trial'
    SUBSCRIPTION_STATUS_ACTIVE = 'active'
    SUBSCRIPTION_STATUS_PAST_DUE = 'past_due'
    SUBSCRIPTION_STATUS_EXPIRED = 'expired'
    SUBSCRIPTION_STATUS_CANCELED = 'canceled'
    
    SUBSCRIPTION_CHOICES = [
        (SUBSCRIPTION_STATUS_FREE, 'Free'),
        (SUBSCRIPTION_STATUS_TRIAL, 'Trial'),
        (SUBSCRIPTION_STATUS_ACTIVE, 'Active'),
        (SUBSCRIPTION_STATUS_PAST_DUE, 'Past Due'),
        (SUBSCRIPTION_STATUS_EXPIRED, 'Expired'),
        (SUBSCRIPTION_STATUS_CANCELED, 'Canceled'),
    ]

    SUBSCRIPTION_PLAN_FREE = 'FREE'
    SUBSCRIPTION_PLAN_PRO = 'PRO'

    SUBSCRIPTION_PLAN_CHOICES = [
        (SUBSCRIPTION_PLAN_FREE, 'Free'),
        (SUBSCRIPTION_PLAN_PRO, 'Pro'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(unique=True, max_length=255, db_index=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_organizations',
        help_text="The super-admin of this organization"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Billing/Subscription fields
    subscription_plan = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_PLAN_CHOICES,
        default=SUBSCRIPTION_PLAN_FREE,
        db_index=True,
        help_text="Subscription tier (Free vs Pro)"
    )

    subscription_status = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_CHOICES,
        default=SUBSCRIPTION_STATUS_FREE,
        db_index=True,
        help_text="Current subscription status"
    )
    stripe_customer_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text="Stripe Customer ID for this organization"
    )
    stripe_subscription_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text="Stripe Subscription ID"
    )
    subscription_started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the subscription became active"
    )
    subscription_ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the subscription expires or ends"
    )
    trial_start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the 15-day trial started"
    )

    # Alerting
    slack_webhook_url = models.URLField(
        null=True,
        blank=True,
        help_text="Slack Webhook URL for regression alerts"
    )

    @property
    def is_in_trial(self) -> bool:
        """Check if organization is currently in valid trial period."""
        if not self.trial_start_date:
            return False
        # Trial is valid if now < trial_start + 15 days
        return timezone.now() < (self.trial_start_date + timedelta(days=15))

    class Meta:
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['owner']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            # Slug generation with uniqueness fallback
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            
            while Organization.objects.filter(slug=slug).exclude(id=self.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_admin_members(self):
        """Get all admin members of this organization."""
        return self.members.filter(role=Membership.ROLE_ADMIN)
    
    def has_admin_members(self) -> bool:
        """Check if organization has at least one admin."""
        return self.members.filter(role=Membership.ROLE_ADMIN).exists()

class Membership(models.Model):
    """
    Linking table between Users and Organizations with RBAC roles.
    
    Industry-Grade Features:
    - UUID primary key for consistency
    - Role-based access control (ADMIN, MEMBER, VIEWER)
    - Unique constraint per user-organization pair
    - Efficient indexing for permission checks
    - Timestamp tracking for audit trails
    """
    ROLE_ADMIN = 'ADMIN'
    ROLE_MEMBER = 'MEMBER'
    ROLE_VIEWER = 'VIEWER'

    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),    # Can change settings, invite users, manage members
        (ROLE_MEMBER, 'Member'),  # Can run audits, view results
        (ROLE_VIEWER, 'Viewer'),  # Read-only access to reports and findings
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='memberships',
        db_index=True
    )
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE,
        related_name='members',
        db_index=True,
        null=True,
        blank=True,
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'organization')
        verbose_name = 'Membership'
        verbose_name_plural = 'Memberships'
        ordering = ['-joined_at']
        indexes = [
            models.Index(fields=['user', 'organization']),
            models.Index(fields=['organization', 'role']),
        ]

    def __str__(self):
        return f"{self.user.email} -> {self.organization.name} ({self.role})"

    def is_admin(self) -> bool:
        """Convenience method to check if user is admin."""
        return self.role == self.ROLE_ADMIN
    
    def can_invite_members(self) -> bool:
        """Check if user can invite members."""
        return self.role == self.ROLE_ADMIN
    
    def can_manage_members(self) -> bool:
        """Check if user can remove/manage members."""
        return self.role == self.ROLE_ADMIN
    
    def can_modify_organization(self) -> bool:
        """Check if user can modify organization settings."""
        return self.role == self.ROLE_ADMIN


class OrganizationInvite(models.Model):
    """
    Invitation tokens for users to join an organization.
    
    Industry-Grade Features:
    - Secure random token generation (cryptographically secure)
    - Status tracking (PENDING, ACCEPTED, EXPIRED)
    - Time-based expiration (configurable TTL)
    - One-time use enforcement
    - Audit trail (created_at, used_at)
    - Prevents duplicate invitations (unique_together)
    """
    
    STATUS_PENDING = 'PENDING'
    STATUS_ACCEPTED = 'ACCEPTED'
    STATUS_EXPIRED = 'EXPIRED'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_EXPIRED, 'Expired'),
    ]
    
    # Invite token TTL (default: 7 days)
    INVITE_EXPIRY_DAYS = 7
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='invites',
        db_index=True,
        null=True,
        blank=True,
    )
    email = models.EmailField(db_index=True)
    role = models.CharField(
        max_length=20,
        choices=Membership.ROLE_CHOICES,
        default=Membership.ROLE_MEMBER
    )
    
    # Secure token for accepting invite (cryptographically random)
    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        editable=False
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True
    )
    
    # Invited by (audit trail)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_invites'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)
    
    # Track accepted by (for audit)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accepted_invites'
    )
    
    class Meta:
        unique_together = ('organization', 'email', 'status')
        verbose_name = 'Organization Invite'
        verbose_name_plural = 'Organization Invites'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'email']),
            models.Index(fields=['status']),
            models.Index(fields=['expires_at']),
        ]
        constraints = [
            # Prevent duplicate pending invites to same email in same org
            models.UniqueConstraint(
                fields=['organization', 'email'],
                condition=Q(status='PENDING'),
                name='unique_pending_invite_per_email'
            ),
        ]
    
    def __str__(self):
        return f"Invite {self.email} to {self.organization.name}"
    
    @staticmethod
    def generate_token() -> str:
        """
        Generate a cryptographically secure random token.
        
        Returns:
            str: 64-character hex string
        """
        return secrets.token_hex(32)
    
    def save(self, *args, **kwargs):
        """Auto-generate token and expiry on creation."""
        if not self.token:  # Only if token not already set
            # Generate secure token
            self.token = self.generate_token()
        
        if not self.expires_at:  # Only if expiry not already set
            # Set expiry to 7 days from now
            self.expires_at = timezone.now() + timedelta(days=self.INVITE_EXPIRY_DAYS)
        
        super().save(*args, **kwargs)
    
    def is_expired(self) -> bool:
        """Check if invite has expired."""
        if self.status != self.STATUS_PENDING:
            return False
        return timezone.now() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if invite can be accepted (not expired, still pending)."""
        return (
            self.status == self.STATUS_PENDING
            and not self.is_expired()
        )
    
    def mark_expired(self):
        """Mark invite as expired."""
        if self.status == self.STATUS_PENDING:
            self.status = self.STATUS_EXPIRED
            self.save(update_fields=['status'])
    
    def accept(self, user: 'User') -> 'Membership':
        """
        Accept the invite and create a membership.
        
        Args:
            user: The User accepting the invite
            
        Returns:
            Membership: The newly created membership
            
        Raises:
            ValidationError: If invite is not valid
        """
        if not self.is_valid():
            raise ValidationError("This invite is no longer valid or has expired.")
        
        # Check if user already has membership
        if Membership.objects.filter(
            user=user,
            organization=self.organization
        ).exists():
            raise ValidationError(
                f"User {user.email} is already a member of {self.organization.name}"
            )
        
        # Create membership
        membership = Membership.objects.create(
            user=user,
            organization=self.organization,
            role=self.role
        )
        
        # Mark invite as accepted
        self.status = self.STATUS_ACCEPTED
        self.used_at = timezone.now()
        self.accepted_by = user
        self.save(update_fields=['status', 'used_at', 'accepted_by'])
        
        return membership
    
    def clean(self):
        """Validation for the model."""
        super().clean()
        
        # Validate that organization exists
        if not self.organization_id:
            raise ValidationError({'organization': 'Organization is required.'})
        
        # Validate email
        if not self.email:
            raise ValidationError({'email': 'Email is required.'})
        
        # Prevent inviting the organization owner
        if self.organization.owner.email == self.email:
            raise ValidationError({
                'email': 'Cannot invite the organization owner.'
            })
        
        # Prevent duplicate active invites
        if not self.pk:  # Only on creation
            existing = OrganizationInvite.objects.filter(
                organization=self.organization,
                email=self.email,
                status=self.STATUS_PENDING
            ).first()
            
            if existing and not existing.is_expired():
                raise ValidationError({
                    'email': 'This user has already been invited. Invite expires at ' +
                            existing.expires_at.isoformat()
                })


class ActivityLog(models.Model):
    """
    Audit trail for important actions within an organization.
    
    Examples:
    - User A invited User B
    - User A changed Organization Settings
    - User A deleted User C
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='activity_logs',
        db_index=True
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activity_logs'
    )
    action = models.CharField(max_length=255, help_text="Description of the action")
    
    # Generic relation to target object (optional)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.CharField(max_length=255, null=True, blank=True)
    target = GenericForeignKey('content_type', 'object_id')
    
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional context")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'created_at']),
        ]

    def __str__(self):
        return f"{self.actor} {self.action} in {self.organization}"