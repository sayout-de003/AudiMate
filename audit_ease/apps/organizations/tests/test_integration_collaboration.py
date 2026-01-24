import pytest
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User
from apps.organizations.models import OrganizationInvite, Membership

@pytest.mark.django_db
def test_collaboration_flow(admin_client, organization):
    """
    Test the Collaboration Flow:
    1. Admin invites a new user.
    2. New user accepts the invite.
    3. Verify membership.
    """
    
    # 1. Invite Member
    # Endpoint: POST /api/v1/organizations/{id}/invite_member/
    invite_url = f'/api/v1/organizations/{organization.id}/invite_member/'
    invite_payload = {
        "email": "collab_new@example.com",
        "role": Membership.ROLE_MEMBER
    }
    
    response = admin_client.post(invite_url, invite_payload)
    assert response.status_code == status.HTTP_201_CREATED
    
    # Get the invite token from DB
    # (Token is typically not returned in API response for security reasons, delivered via email)
    invite = OrganizationInvite.objects.get(email="collab_new@example.com", organization=organization)
    token = invite.token
    assert token is not None
    
    # 2. Accept Invite
    # We need a new user to accept it (simulating they clicked link and maybe registered/logged in)
    new_user = User.objects.create_user(
        email="collab_new@example.com",
        password="Password123!",
        first_name="Collab",
        last_name="User"
    )
    
    # Create a client for the new user
    new_user_client = APIClient()
    new_user_client.force_authenticate(user=new_user)
    
    accept_url = '/api/v1/invites/accept/'
    accept_payload = {
        "token": token
    }
    
    response = new_user_client.post(accept_url, accept_payload)
    assert response.status_code == status.HTTP_201_CREATED
    
    # 3. Verify Membership
    assert Membership.objects.filter(user=new_user, organization=organization).exists()
    membership = Membership.objects.get(user=new_user, organization=organization)
    assert membership.role == Membership.ROLE_MEMBER
