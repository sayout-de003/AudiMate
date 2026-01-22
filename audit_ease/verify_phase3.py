import os
import sys
import django

# Configure Django settings before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

django.setup()

# 1. Setup Environment
print("--- STARTING PHASE 3.5 VERIFICATION (FIXED) ---")
from apps.organizations.models import Organization
from apps.users.models import User
from apps.integrations.models import Integration
from apps.audits.models import Audit, Question, Evidence
from apps.audits.logic import AuditExecutor
from apps.integrations.views import GitHubWebhookView
from django.test import RequestFactory

# 2. Setup Test Data
print("\n[SETUP] Creating Test Data...")
if not User.objects.filter(email='test@verify.com').exists():
    user = User.objects.create_user(email='test@verify.com', password='password')
else:
    user = User.objects.get(email='test@verify.com')

if not Organization.objects.filter(name='Verify Corp').exists():
    org = Organization.objects.create(name='Verify Corp', owner=user)
    # Note: Signal auto-creates ADMIN membership for owner, no need to add manually
else:
    org = Organization.objects.get(name='Verify Corp')

print("✓ User and Organization ready")

# --- CHECK 1: INTEGRATION STABILITY ---
print("\n[CHECK 1] Integration Model Stability")
try:
    Integration.objects.filter(name='Test AWS Verify').delete()
    
    # FIX: Use the property accessors instead of set_token/get_token
    integ = Integration.objects.create(
        organization=org,
        provider='aws',
        name='Test AWS Verify'
    )
    
    test_token = {'access_key': 'AKIATEST123', 'secret_key': 'SECRET123'}
    # Use property setter which handles encryption automatically
    integ.access_token = test_token['access_key']
    integ.refresh_token = test_token['secret_key']
    integ.save()
    
    # Use property getter to decrypt
    retrieved_access = integ.access_token
    retrieved_refresh = integ.refresh_token
    
    if retrieved_access == test_token['access_key'] and retrieved_refresh == test_token['secret_key']:
        print("✅ PASS: Integration created and token encrypted/decrypted successfully.")
    else:
        print(f"❌ FAIL: Token mismatch. Got access: {retrieved_access}")
except Exception as e:
    print(f"❌ FAIL: Integration Model crashed: {e}")

# --- CHECK 2: REAL AUDIT LOGIC ---
print("\n[CHECK 2] Real Audit Execution")
try:
    audit = Audit.objects.create(organization=org, triggered_by=user)
    
    print("   Running AuditExecutor... (Expect connection errors, but NOT sleep)")
    
    # FIX: Pass 'audit.id' and call execute_checks() instead of run()
    executor = AuditExecutor(audit.id)
    
    try:
        checks = executor.execute_checks()
        print(f"   ✓ Audit executed {checks} checks")
    except Exception as e:
        # Expected failure due to fake AWS keys
        print(f"   (System attempted connection: {str(e)[:80]}...)")
    
    evidence_count = Evidence.objects.filter(audit=audit).count()
    if evidence_count > 0:
        print(f"✅ PASS: Audit Logic executed and created {evidence_count} evidence items.")
    else:
        print("❌ FAIL: No evidence created. Logic might still be mocked.")

except Exception as e:
    print(f"❌ FAIL: Audit Logic crashed: {e}")

# --- CHECK 3: WEBHOOK SECURITY ---
print("\n[CHECK 3] Webhook Security")
try:
    factory = RequestFactory()
    view = GitHubWebhookView.as_view()
    
    # Case A: Request WITHOUT Signature
    request_no_sig = factory.post('/api/v1/integrations/webhooks/github/', 
                                  data={'ref': 'refs/heads/main'}, 
                                  content_type='application/json')
    response_no_sig = view(request_no_sig)
    
    # FIX: Accept 401 as a valid rejection code
    if response_no_sig.status_code in [401, 403, 400]:
         print(f"✅ PASS: Webhook correctly rejected unsigned request (Status {response_no_sig.status_code}).")
    else:
         print(f"❌ FAIL: Webhook accepted unsigned request (Status {response_no_sig.status_code})")

except Exception as e:
    print(f"❌ FAIL: Webhook check crashed: {e}")

print("\n--- VERIFICATION COMPLETE ---")

