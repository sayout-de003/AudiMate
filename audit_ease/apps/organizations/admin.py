# apps/organizations/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Q
from .models import Organization, Membership, OrganizationInvite


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Admin for Organization model."""
    list_display = ('name', 'owner_email', 'subscription_plan', 'subscription_status', 'member_count', 'admin_count', 'created_at')
    list_editable = ('subscription_plan', 'subscription_status')
    list_filter = ('subscription_plan', 'subscription_status', 'created_at', 'updated_at')
    search_fields = ('name', 'slug', 'owner__email')
    readonly_fields = ('id', 'slug', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'name', 'slug', 'owner')
        }),
        ('Subscription', {
            'fields': ('subscription_plan', 'subscription_status', 'stripe_customer_id', 'stripe_subscription_id'),
            'classes': ('collapse',),
            'description': 'Manage billing details manually.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def owner_email(self, obj):
        return obj.owner.email
    owner_email.short_description = 'Owner Email'

    def member_count(self, obj):
        count = obj.members.count()
        return format_html(
            '<a href="{}?organization__id={}">{} members</a>',
            reverse('admin:organizations_membership_changelist'),
            obj.id,
            count
        )
    member_count.short_description = 'Members'

    def admin_count(self, obj):
        count = obj.get_admin_members().count()
        return format_html('{} admins', count)
    admin_count.short_description = 'Admins'


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """Admin for Membership model."""
    list_display = ('user_email', 'organization_name', 'role', 'joined_at')
    list_filter = ('role', 'joined_at', 'organization')
    search_fields = ('user__email', 'organization__name')
    readonly_fields = ('id', 'joined_at', 'updated_at')
    
    fieldsets = (
        ('Membership Info', {
            'fields': ('id', 'user', 'organization', 'role')
        }),
        ('Timestamps', {
            'fields': ('joined_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'

    def organization_name(self, obj):
        return obj.organization.name
    organization_name.short_description = 'Organization'
    organization_name.admin_order_field = 'organization__name'


@admin.register(OrganizationInvite)
class OrganizationInviteAdmin(admin.ModelAdmin):
    """Admin for OrganizationInvite model."""
    list_display = (
        'email',
        'organization_name',
        'role',
        'status_badge',
        'invited_by_email',
        'expires_at',
        'created_at'
    )
    list_filter = ('status', 'role', 'created_at', 'expires_at', 'organization')
    search_fields = ('email', 'organization__name', 'invited_by__email')
    readonly_fields = ('id', 'token', 'created_at', 'expires_at', 'used_at')
    
    fieldsets = (
        ('Invitation Details', {
            'fields': ('id', 'organization', 'email', 'role', 'status')
        }),
        ('Token', {
            'fields': ('token',),
            'classes': ('collapse',),
            'description': 'Do not share this token. Regenerate if compromised.'
        }),
        ('Audit Trail', {
            'fields': ('invited_by', 'created_at', 'expires_at', 'accepted_by', 'used_at'),
            'classes': ('collapse',)
        }),
    )

    def organization_name(self, obj):
        return obj.organization.name
    organization_name.short_description = 'Organization'
    organization_name.admin_order_field = 'organization__name'

    def invited_by_email(self, obj):
        return obj.invited_by.email if obj.invited_by else 'System'
    invited_by_email.short_description = 'Invited By'

    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            OrganizationInvite.STATUS_PENDING: '#FFA500',  # Orange
            OrganizationInvite.STATUS_ACCEPTED: '#00AA00',  # Green
            OrganizationInvite.STATUS_EXPIRED: '#AA0000',   # Red
        }
        color = colors.get(obj.status, '#999999')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    actions = ['mark_expired']

    def mark_expired(self, request, queryset):
        """Action to mark pending invites as expired."""
        pending = queryset.filter(status=OrganizationInvite.STATUS_PENDING)
        updated = pending.update(status=OrganizationInvite.STATUS_EXPIRED)
        self.message_user(request, f'{updated} invitations marked as expired.')
    mark_expired.short_description = 'Mark selected as expired'
