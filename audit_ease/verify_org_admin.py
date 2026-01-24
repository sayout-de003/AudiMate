
import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.contrib.auth import get_user_model
from apps.organizations.models import Organization, Membership, ActivityLog
from apps.organizations.views_admin import AdminDashboardView, MemberViewSet
from apps.organizations.serializers_admin import OrgDashboardStatsSerializer
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.exceptions import ValidationError

User = get_user_model()

def run_verification():
    print("--- Verifying Organization Admin Module ---")
    
    # 1. Setup Data
    email = "admin_verify@example.com"
    user = User.objects.filter(email=email).first()
    if not user:
        user = User.objects.create_user(email=email, password="password123")
    
    org_name = "Verify Org"
    org = Organization.objects.filter(name=org_name).first()
    if not org:
        org = Organization.objects.create(name=org_name, owner=user)
        # Owner automatically gets admin membership usually, but ensure it
        Membership.objects.get_or_create(user=user, organization=org, role=Membership.ROLE_ADMIN)
    
    print(f"User: {user.email}, Org: {org.name} ({org.id})")

    # 2. Test Dashboard Logic
    print("\n[Test] Dashboard Stats")
    factory = APIRequestFactory()
    request = factory.get(f'/api/v1/orgs/{org.id}/admin/dashboard/')
    force_authenticate(request, user=user)
    
    view = AdminDashboardView.as_view()
    response = view(request, org_id=org.id)
    
    print(f"Status: {response.status_code}")
    print(f"Data: {response.data}")
    
    assert response.status_code == 200
    assert 'total_members' in response.data
    
    # 3. Test Member Delete Protection (Last Admin)
    print("\n[Test] Last Admin Protection")
    # Try to delete self (the only admin)
    member = Membership.objects.get(user=user, organization=org)
    
    view_set = MemberViewSet()
    view_set.request = request
    view_set.request.user = user
    view_set.kwargs = {'org_id': org.id}
    
    try:
        view_set.perform_destroy(member)
        print("ERROR: Should have raised ValidationError")
    except ValidationError as e:
        print(f"SUCCESS: Caught expected validation error: {e}")
    except Exception as e:
        print(f"ERROR: Caught unexpected exception: {type(e)} {e}")

    # 4. Test Activity Log Creation
    print("\n[Test] Activity Log")
    # Create a dummy log to verify model
    log = ActivityLog.objects.create(
        organization=org,
        actor=user,
        action="Test Action",
        metadata={"foo": "bar"}
    )
    print(f"Created Log: {log}")
    assert log.pk is not None

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    run_verification()
