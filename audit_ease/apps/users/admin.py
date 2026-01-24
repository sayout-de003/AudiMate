# apps/users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import User
from .verification import EmailVerification


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Comprehensive User Admin for managing all registered users.
    Allows superuser to view, edit, and delete malicious accounts.
    """
    list_display = (
        'email',
        'full_name_display',
        'email_verified_badge',
        'is_active_badge',
        'is_staff',
        'is_superuser',
        'organization_count',
        'date_joined'
    )
    list_filter = (
        'is_active',
        'is_staff',
        'is_superuser',
        'email_verified',
        'date_joined',
        'last_login'
    )
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    # Read-only fields to prevent accidental corruption
    readonly_fields = (
        'id',
        'date_joined',
        'last_login',
        'password',
        'organization_list'
    )
    
    fieldsets = (
        ('Authentication', {
            'fields': ('email', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name')
        }),
        ('Verification Status', {
            'fields': ('email_verified', 'is_active'),
            'description': 'Control user access and email verification status'
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Organizations', {
            'fields': ('organization_list',),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('date_joined', 'last_login'),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('id',),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
    
    # Custom display methods
    def full_name_display(self, obj):
        """Display full name."""
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name if name else '-'
    full_name_display.short_description = 'Full Name'
    full_name_display.admin_order_field = 'first_name'
    
    def email_verified_badge(self, obj):
        """Show email verification status with color coding."""
        if obj.email_verified:
            return format_html(
                '<span style="background-color: #00AA00; color: white; padding: 3px 10px; '
                'border-radius: 3px;">✓ Verified</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #FFA500; color: white; padding: 3px 10px; '
                'border-radius: 3px;">✗ Not Verified</span>'
            )
    email_verified_badge.short_description = 'Email Status'
    email_verified_badge.admin_order_field = 'email_verified'
    
    def is_active_badge(self, obj):
        """Show account active status with color coding."""
        if obj.is_active:
            return format_html(
                '<span style="background-color: #00AA00; color: white; padding: 3px 10px; '
                'border-radius: 3px;">Active</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #AA0000; color: white; padding: 3px 10px; '
                'border-radius: 3px;">Inactive</span>'
            )
    is_active_badge.short_description = 'Account Status'
    is_active_badge.admin_order_field = 'is_active'
    
    def organization_count(self, obj):
        """Show count of organizations user belongs to with link."""
        from apps.organizations.models import Membership
        count = Membership.objects.filter(user=obj).count()
        if count > 0:
            return format_html(
                '<a href="{}?user__id={}">{} orgs</a>',
                reverse('admin:organizations_membership_changelist'),
                obj.id,
                count
            )
        return '0 orgs'
    organization_count.short_description = 'Organizations'
    
    def organization_list(self, obj):
        """Display list of organizations with roles."""
        from apps.organizations.models import Membership
        memberships = Membership.objects.filter(user=obj).select_related('organization')
        if not memberships.exists():
            return 'No organizations'
        
        html = '<ul>'
        for m in memberships:
            html += f'<li><strong>{m.organization.name}</strong> - {m.get_role_display()}</li>'
        html += '</ul>'
        return format_html(html)
    organization_list.short_description = 'Organization Memberships'
    
    # Custom actions for bulk operations
    actions = [
        'mark_as_verified',
        'mark_as_unverified',
        'activate_users',
        'deactivate_users',
        'delete_malicious_users'
    ]
    
    def mark_as_verified(self, request, queryset):
        """Mark selected users as email verified."""
        updated = queryset.update(email_verified=True)
        self.message_user(request, f'{updated} users marked as verified.')
    mark_as_verified.short_description = 'Mark as email verified'
    
    def mark_as_unverified(self, request, queryset):
        """Mark selected users as NOT email verified."""
        updated = queryset.update(email_verified=False)
        self.message_user(request, f'{updated} users marked as NOT verified.')
    mark_as_unverified.short_description = 'Mark as NOT verified'
    
    def activate_users(self, request, queryset):
        """Activate selected user accounts."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} users activated.')
    activate_users.short_description = 'Activate selected users'
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected user accounts (soft delete)."""
        # Don't deactivate superusers
        queryset = queryset.filter(is_superuser=False)
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} users deactivated. Superusers were excluded for safety.'
        )
    deactivate_users.short_description = 'Deactivate selected users'
    
    def delete_malicious_users(self, request, queryset):
        """Hard delete malicious users (DANGEROUS - requires confirmation)."""
        # Safety: Don't delete superusers or staff
        safe_queryset = queryset.filter(is_superuser=False, is_staff=False)
        count = safe_queryset.count()
        safe_queryset.delete()
        self.message_user(
            request,
            f'{count} malicious users permanently deleted. Staff/superusers were excluded.'
        )
    delete_malicious_users.short_description = '🚨 PERMANENTLY DELETE selected users'


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    """
    Admin for email OTP verification codes.
    Useful for debugging verification issues or manually verifying users.
    """
    list_display = (
        'user_email',
        'email',
        'otp_code_display',
        'is_verified_badge',
        'is_expired_badge',
        'attempts',
        'created_at',
        'expires_at'
    )
    list_filter = (
        'is_verified',
        'created_at',
        'expires_at'
    )
    search_fields = ('user__email', 'email', 'otp_code')
    readonly_fields = ('id', 'created_at', 'expires_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Verification Details', {
            'fields': ('id', 'user', 'email', 'otp_code')
        }),
        ('Status', {
            'fields': ('is_verified', 'attempts')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'expires_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        """Display user email with link to user admin."""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:users_user_change', args=[obj.user.id]),
            obj.user.email
        )
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def otp_code_display(self, obj):
        """Display OTP code with monospace font."""
        return format_html(
            '<code style="background: #f0f0f0; padding: 2px 6px; '
            'border-radius: 3px; font-size: 14px;">{}</code>',
            obj.otp_code
        )
    otp_code_display.short_description = 'OTP Code'
    otp_code_display.admin_order_field = 'otp_code'
    
    def is_verified_badge(self, obj):
        """Show verification status."""
        if obj.is_verified:
            return format_html(
                '<span style="background-color: #00AA00; color: white; padding: 3px 10px; '
                'border-radius: 3px;">✓ Verified</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #FFA500; color: white; padding: 3px 10px; '
                'border-radius: 3px;">Pending</span>'
            )
    is_verified_badge.short_description = 'Status'
    is_verified_badge.admin_order_field = 'is_verified'
    
    def is_expired_badge(self, obj):
        """Show expiration status."""
        if obj.is_expired():
            return format_html(
                '<span style="background-color: #AA0000; color: white; padding: 3px 10px; '
                'border-radius: 3px;">Expired</span>'
            )
        else:
            time_left = obj.expires_at - timezone.now()
            minutes = int(time_left.total_seconds() / 60)
            return format_html(
                '<span style="background-color: #00AA00; color: white; padding: 3px 10px; '
                'border-radius: 3px;">{} min left</span>',
                minutes
            )
    is_expired_badge.short_description = 'Expiration'
    
    actions = ['mark_as_verified', 'delete_expired']
    
    def mark_as_verified(self, request, queryset):
        """Manually mark OTP codes as verified."""
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} OTP codes marked as verified.')
    mark_as_verified.short_description = 'Mark as verified'
    
    def delete_expired(self, request, queryset):
        """Delete expired OTP codes."""
        now = timezone.now()
        expired = queryset.filter(expires_at__lt=now)
        count = expired.count()
        expired.delete()
        self.message_user(request, f'{count} expired OTP codes deleted.')
    delete_expired.short_description = 'Delete expired codes'
