import pytest
from rest_framework.test import APIClient
from apps.users.models import User
from apps.organizations.models import Organization, Membership

@pytest.fixture
def api_client():
    return APIClient()

from allauth.socialaccount.models import SocialAccount

@pytest.fixture
def user(db):
    """Create a standard user with GitHub connected."""
    user = User.objects.create_user(
        email='testuser@example.com',
        password='strongpassword123',
        first_name='Test',
        last_name='User'
    )
    # Connect GitHub account primarily for AuditStartView
    SocialAccount.objects.create(
        user=user,
        provider='github',
        uid='123456',
        extra_data={'login': 'testuser'}
    )
    return user

@pytest.fixture
def authenticated_client(api_client, user):
    """Return an APIClient authenticated as the standard user."""
    api_client.force_authenticate(user=user)
    return api_client

@pytest.fixture
def organization(db, user):
    """Create an organization owned by the user."""
    org = Organization.objects.create(
        name='Test Org',
        owner=user,
        subscription_status=Organization.SUBSCRIPTION_STATUS_ACTIVE
    )
    return org

@pytest.fixture
def admin_user(db):
    """Create a second user to act as another admin or specific role if needed."""
    return User.objects.create_user(
        email='admin@example.com',
        password='adminpassword123',
        first_name='Admin',
        last_name='User'
    )

@pytest.fixture
def admin_client(api_client, organization, user):
    """
    Return an APIClient authenticated as the organization admin (the owner).
    Uses session auth (force_login) to satisfy standard Django mixins,
    and force_authenticate for DRF.
    """
    api_client.force_login(user)
    api_client.force_authenticate(user=user)
    return api_client
