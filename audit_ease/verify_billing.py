import os
import django
from datetime import timedelta
from django.utils import timezone
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from apps.users.models import User
from apps.organizations.models import Organization
from apps.audits.models import Audit, Evidence, Question
from apps.core.permissions import HasGeneralAccess, CheckTrialQuota, HasPremiumFeatureAccess
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
import uuid

def setup_test_data():
    print("Setting up test data...")
    email = f"test_billing_{uuid.uuid4()}@example.com"
    user = User.objects.create_user(email=email, password="password123")
    
    org_name = f"Test Org {uuid.uuid4()}"
    org = Organization.objects.create(name=org_name, owner=user)
    # Default is Free, but let's set it to Trial explicit
    org.subscription_status = Organization.SUBSCRIPTION_STATUS_TRIAL
    org.trial_start_date = timezone.now()
    org.save()
    
    # Ensure membership (model usually handles creating owner membership somewhere, but doing explicit)
    # Actually Organization.save doesn't seem to create membership, so let's check
    from apps.organizations.models import Membership
    Membership.objects.get_or_create(user=user, organization=org, role=Membership.ROLE_ADMIN)
    
    return user, org

def test_permissions():
    user, org = setup_test_data()
    factory = APIRequestFactory()
    
    # Mock Request
    request = factory.get('/')
    request.user = user
    # Mock middleware setting org (User usually has wrapper or we assume get_organization works)
    # We will manually mock get_organization if needed, but the permission uses request.user.get_organization()
    # Let's ensure get_organization works.
    
    print(f"Testing permissions for Org: {org.name} Status: {org.subscription_status}")
    
    # 1. Test HasGeneralAccess (Should Pass in Trial)
    perm = HasGeneralAccess()
    view = APIView()
    assert perm.has_permission(request, view) == True, "HasGeneralAccess failed for ACTIVE Trial"
    print("✅ HasGeneralAccess passed for ACTIVE Trial")
    
    # 2. Test HasPremiumFeatureAccess (Should Fail in Trial)
    perm_prem = HasPremiumFeatureAccess()
    assert perm_prem.has_permission(request, view) == False, "HasPremiumFeatureAccess passed for TRIAL (Should Fail)"
    print("✅ HasPremiumFeatureAccess blocked TRIAL user")
    
    # 3. Test Quota (Evidence < 50)
    perm_quota = CheckTrialQuota()
    assert perm_quota.has_permission(request, view) == True, "CheckTrialQuota failed for 0 evidence"
    print("✅ CheckTrialQuota passed for 0 evidence")
    
    # Create audit
    audit = Audit.objects.create(organization=org, triggered_by=user)
    evidences = []
    questions = []
    for i in range(50):
        q = Question.objects.create(key=f"q_{uuid.uuid4()}", title=f"Test Q {i}", severity="LOW")
        questions.append(q)
        evidences.append(Evidence(audit=audit, question=q, status='PASS', comment=f"ev {i}"))
    Evidence.objects.bulk_create(evidences)
    
    # Test Quota again (Should Fail on 51st attempt Check)
    # The permission checks if count >= 50.
    # Note: Logic was `if count >= 50: return False`. So if we HAVE 50, and try to create 51st, it should fail.
    # Current count is 50.
    assert perm_quota.has_permission(request, view) == False, "CheckTrialQuota passed with 50 items (Should Fail)"
    print("✅ CheckTrialQuota blocked creation at 50 items")
    
    # 4. Test Expired Trial
    print("Simulating Expired Trial...")
    org.trial_start_date = timezone.now() - timedelta(days=16)
    org.save()
    
    assert perm.has_permission(request, view) == False, "HasGeneralAccess passed for EXPIRED Trial (Should Fail)"
    print("✅ HasGeneralAccess blocked EXPIRED Trial")
    
    # 5. Test Active Subscription
    print("Upgrading to Active...")
    org.subscription_status = Organization.SUBSCRIPTION_STATUS_ACTIVE
    org.save()
    
    assert perm.has_permission(request, view) == True, "HasGeneralAccess failed for ACTIVE Subscription"
    assert perm_prem.has_permission(request, view) == True, "HasPremiumFeatureAccess failed for ACTIVE Subscription"
    assert perm_quota.has_permission(request, view) == True, "CheckTrialQuota failed for ACTIVE (Should be unlimited)"
    print("✅ All permissions passed for ACTIVE Subscription")

if __name__ == "__main__":
    try:
        test_permissions()
        print("\n🎉 All Verification Tests Passed!")
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
