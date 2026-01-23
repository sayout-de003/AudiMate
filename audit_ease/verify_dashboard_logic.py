import os
import django
import sys
from django.utils import timezone

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
try:
    django.setup()
except Exception as e:
    print(f"Django setup failed: {e}")
    sys.exit(1)

from django.contrib.auth import get_user_model
from apps.organizations.models import Organization, Membership
from apps.audits.models import Audit, Evidence, Question
from apps.audits.services.stats_service import AuditStatsService
from rest_framework.test import APIRequestFactory, force_authenticate
from apps.audits.views import DashboardStatsView

User = get_user_model()

def run_verification():
    print("Setting up verification data...")
    
    # 1. Cleanup
    import uuid
    random_id = str(uuid.uuid4())[:8]
    email = f"stats_test_{random_id}@example.com"
    org_name = f"Stats Test Org {random_id}"
    try:
        u = User.objects.filter(email=email).first()
        if u:
            u.delete()
        Organization.objects.filter(name="Stats Test Org").delete()
    except Exception as e:
        print(f"Cleanup warning: {e}")
    
    # 2. Create User & Org
    user = User.objects.create_user(email=email, password="password123")
    org = Organization.objects.create(name=org_name, owner=user)
    # Membership auto-created by signal for owner
    # Membership.objects.create(user=user, organization=org, role='ADMIN')
    
    # 3. Create Questions (if not exist)
    q1, _ = Question.objects.get_or_create(key="q1", defaults={"title": "Q1", "severity": "CRITICAL", "description": "desc"})
    q2, _ = Question.objects.get_or_create(key="q2", defaults={"title": "Q2", "severity": "LOW", "description": "desc"})
    q3, _ = Question.objects.get_or_create(key="q3", defaults={"title": "Q3", "severity": "MEDIUM", "description": "desc"})
    q4, _ = Question.objects.get_or_create(key="q4", defaults={"title": "Q4", "severity": "HIGH", "description": "desc"})
    
    # 4. Create Audit
    audit = Audit.objects.create(organization=org, triggered_by=user, status='COMPLETED')
    
    # 5. Create Evidence
    # 2 Pass, 1 Fail Critical, 1 Fail Low => Total 4. Pass Rate 50%.
    Evidence.objects.create(audit=audit, question=q3, status='PASS')
    Evidence.objects.create(audit=audit, question=q4, status='PASS')
    Evidence.objects.create(audit=audit, question=q1, status='FAIL') # Critical Fail
    Evidence.objects.create(audit=audit, question=q2, status='FAIL') # Low Fail
    
    print(f"Audit {audit.id} created with 4 evidence items (2 PASS, 2 FAIL).")
    
    # 6. Verify Service Logic
    print("\n--- Verifying AuditStatsService ---")
    stats = AuditStatsService.calculate_audit_stats(audit)
    print(f"Stats: {stats}")
    
    assert stats['total_findings'] == 4, f"Expected 4 total, got {stats['total_findings']}"
    assert stats['passed_count'] == 2, f"Expected 2 passed, got {stats['passed_count']}"
    assert stats['failed_count'] == 2, f"Expected 2 failed, got {stats['failed_count']}"
    assert stats['critical_count'] == 1, f"Expected 1 critical fail, got {stats['critical_count']}"
    assert stats['pass_rate_percentage'] == 50.0, f"Expected 50.0% pass rate, got {stats['pass_rate_percentage']}"
    print("✅ Service Logic Verified")
    
    # 7. Verify API Logic
    print("\n--- Verifying DashboardStatsView ---")
    factory = APIRequestFactory()
    request = factory.get('/api/v1/audits/dashboard/stats/')
    force_authenticate(request, user=user)
    
    view = DashboardStatsView.as_view()
    response = view(request)
    
    print(f"API Response Status: {response.status_code}")
    data = response.data
    # print(f"API Response Data: {data}")
    
    assert response.status_code == 200
    assert data['has_audits'] is True
    assert data['latest_audit_id'] == str(audit.id)
    assert data['stats']['critical_count'] == 1
    assert data['stats']['pass_rate_percentage'] == 50.0
    print("✅ API Logic Verified")
    
    # 8. Verify Empty State
    print("\n--- Verifying Empty State ---")
    # Delete audit
    audit.delete()
    
    request = factory.get('/api/v1/audits/dashboard/stats/')
    force_authenticate(request, user=user)
    response = view(request)
    data = response.data
    
    assert data['has_audits'] is False
    assert "Run your first audit" in data['message']
    print("✅ Empty State Verified")
    
    print("\n🎉 ALL CHECKS PASSED")

if __name__ == "__main__":
    run_verification()
