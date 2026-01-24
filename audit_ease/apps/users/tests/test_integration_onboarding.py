import pytest
from rest_framework import status
from apps.users.models import User
from apps.organizations.models import Organization, Membership

@pytest.mark.django_db
def test_onboarding_flow(api_client):
    """
    Test the full onboarding flow:
    1. User registers
    2. User creates an organization
    3. User is automatically assigned as Admin
    """
    
    # 1. Register a new user
    register_url = '/api/v1/auth/register/'
    register_data = {
        "email": "integration_new@example.com",
        "first_name": "Integration",
        "last_name": "TestUser",
        "password": "StrongPassword123!",
        "password_confirm": "StrongPassword123!"
    }
    
    response = api_client.post(register_url, register_data)
    assert response.status_code == status.HTTP_201_CREATED
    
    # 2. Verify User Creation
    user = User.objects.get(email="integration_new@example.com")
    assert user.first_name == "Integration"
    assert user.check_password("StrongPassword123!")
    
    # 3. Authenticate as the new user
    api_client.force_authenticate(user=user)
    
    # 4. Create a new Organization
    org_url = '/api/v1/organizations/'
    org_data = {
        "name": "Integration Corp"
    }
    
    response = api_client.post(org_url, org_data)
    assert response.status_code == status.HTTP_201_CREATED
    org_id = response.data['id']
    
    # 5. Verify Organization and Permissions
    org = Organization.objects.get(id=org_id)
    assert org.name == "Integration Corp"
    assert org.owner == user
    
    # Verify Membership
    membership = Membership.objects.get(user=user, organization=org)
    assert membership.role == Membership.ROLE_ADMIN
