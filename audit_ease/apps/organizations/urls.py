"""
Organization API URLs

Routes for:
- Organization CRUD operations
- Member invitations
- Member management
- Membership status
"""

from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import (
    OrganizationViewSet,
    accept_invite,
    user_organizations,
    check_invite_validity,
)
from .views_admin import (
    AdminDashboardView,
    MemberViewSet,
    InviteViewSet,
    ActivityLogViewSet,
    OrgSettingsView
)

router = SimpleRouter()
router.register(r'organizations', OrganizationViewSet, basename='organization')

urlpatterns = [
    # Router includes all CRUD routes for organizations
    *router.urls,
    
    # Invite management endpoints (global, not org-specific)
    path('invites/accept/', accept_invite, name='accept-invite'),
    path('invites/check/', check_invite_validity, name='check-invite'),
    
    # User organizations list (convenience endpoint)
    path('user-organizations/', user_organizations, name='user-organizations'),
    
    # Organization Admin Dashboard Routes
    # Base: /api/v1/organizations/{org_id}/admin/
    path('organizations/<uuid:org_id>/admin/dashboard/', AdminDashboardView.as_view(), name='org-admin-dashboard'),
    path('organizations/<uuid:org_id>/admin/members/', MemberViewSet.as_view({'get': 'list'}), name='org-admin-members'),
    path('organizations/<uuid:org_id>/admin/members/<uuid:pk>/', MemberViewSet.as_view({'delete': 'destroy'}), name='org-admin-member-detail'),
    path('organizations/<uuid:org_id>/admin/invites/<uuid:pk>/resend/', InviteViewSet.as_view({'post': 'resend'}), name='org-admin-invite-resend'),
    path('organizations/<uuid:org_id>/admin/logs/', ActivityLogViewSet.as_view({'get': 'list'}), name='org-admin-logs'),
    path('organizations/<uuid:org_id>/admin/settings/', OrgSettingsView.as_view(), name='org-admin-settings'),
]
