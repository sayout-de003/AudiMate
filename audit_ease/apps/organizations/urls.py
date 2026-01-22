"""
Organization API URLs

Routes for:
- Organization CRUD operations
- Member invitations
- Member management
- Membership status
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrganizationViewSet,
    accept_invite,
    user_organizations,
    check_invite_validity,
)

router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet, basename='organization')

urlpatterns = [
    # Router includes all CRUD routes for organizations
    *router.urls,
    
    # Invite management endpoints (global, not org-specific)
    path('invites/accept/', accept_invite, name='accept-invite'),
    path('invites/check/', check_invite_validity, name='check-invite'),
    
    # User organizations list (convenience endpoint)
    path('user-organizations/', user_organizations, name='user-organizations'),
]
