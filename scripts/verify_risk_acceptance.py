
import os
import django
import sys
from datetime import timedelta

# Setup Django Environment
sys.path.append('/Users/sayantande/audit_full_app')
sys.path.append('/Users/sayantande/audit_full_app/audit_ease')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.contrib.auth import get_user_model
from apps.organizations.models import Organization
from apps.audits.models import Audit, Evidence, Question, AuditSnapshot, ScanHistory
from rest_framework.test import APIClient
from django.utils import timezone

User = get_user_model()

def run_verification():
    print("--- Starting Risk Acceptance Verification ---")
    
    # 1. Setup Data
    # Clean previous test data
    email = "test_risk_admin@example.com"
    Organization.objects.filter(name="Test Risk Org").delete()
    User.objects.filter(email=email).delete()
    
    user = User.objects.create_user(email=email, password="password123")
    org = Organization.objects.create(name="Test Risk Org", owner=user)
    # user.organizations.add(org) # Auto-handled by signal/create logic
    
    # Create Question
    q, _ = Question.objects.get_or_create(key="cis_1_1", defaults={"title": "MFA Check", "severity": "CRITICAL"})
    
    # Create Audit (Completed, Score 0)
    audit = Audit.objects.create(
        organization=org,
        status='COMPLETED',
        score=0,
        triggered_by=user,
        created_at=timezone.now()
    )
    
    # Create Failing Evidence
    ev1 = Evidence.objects.create(
        audit=audit,
        question=q,
        status='FAIL',
        raw_data={'repo_name': 'repo-a'},
        comment='MFA not enabled'
    )
    
    print(f"Initial State: Audit Score {audit.score}, Evidence Status {ev1.status}")
    
    # 2. Simulate User "Accepting Risk" via API
    client = APIClient()
    client.force_authenticate(user=user)
    
    url = "/api/v1/audits/risk-accept/"
    data = {
        "check_id": "cis_1_1",
        "reason": "Legacy system, will fix later",
        "resource_identifier": "repo-a"
    }
    
    print(f"Sending Request to {url}...")
    response = client.post(url, data, format='json')
    
    if response.status_code != 201:
        print(f"FAILED: API Error: {response.status_code} - {response.data}")
        return
        
    print(f"API Response: {response.data}")
    
    # 3. Verify Effects
    ev1.refresh_from_db()
    audit.refresh_from_db()
    
    print(f"Post-Action State: Audit Score {audit.score}, Evidence Status {ev1.status}")
    
    # Assertions
    if ev1.status != 'RISK_ACCEPTED':
        print("FAIL: Evidence status did not update to RISK_ACCEPTED")
    elif audit.score != 100: # 1 check, 0 failures (waived) = 100%
        print(f"FAIL: Audit score did not recalculate to 100. Got {audit.score}")
    else:
        print("SUCCESS: Risk accepted and score updated retroactively!")

if __name__ == "__main__":
    run_verification()
