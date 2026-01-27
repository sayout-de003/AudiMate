
from apps.audits.models import Audit, Evidence, Question
from apps.organizations.models import Organization
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from apps.audits.views_export import AuditExportPreviewView
import uuid
import json

User = get_user_model()

def verify_full_verbosity():
    print("Verifying Full Verbosity Audit Report...")
    
    # 1. Setup Data
    email = f"test_auditor_{uuid.uuid4()}@example.com"
    try:
        user = User.objects.create_user(email=email, password="password")
    except:
        user = User.objects.get(email=email) # Should not happen with uuid, but safety
    
    org = Organization.objects.create(
        name="Test Corp Verbosity",
        subscription_status='active',
        owner=user
    )
    
    audit = Audit.objects.create(
        organization=org,
        score=50
    )
    
    # Create Question if needed
    question_pass, _ = Question.objects.get_or_create(
        key="BR_PASS",
        defaults={
            "title": "Branch Protection Pass",
            "description": "Main branch must be protected",
            "severity": "HIGH"
        }
    )
    
    question_fail, _ = Question.objects.get_or_create(
        key="BR_FAIL",
        defaults={
            "title": "Branch Protection Fail",
            "description": "Main branch must be protected",
            "severity": "HIGH"
        }
    )
    
    # Create Evidence (Fail)
    fail_evidence = Evidence.objects.create(
        audit=audit,
        status='FAIL',
        raw_data={
            "repo_name": "backend-repo-FAIL", 
            "branch": "main"
        },
        question=question_fail
    )
    
    # Create Evidence (Pass)
    pass_evidence = Evidence.objects.create(
        audit=audit, 
        status='PASS', 
        question=question_pass,
        raw_data={
            "repo_name": "frontend-repo-PASS",
            "config": "protected"
        }
    )

    # 2. Test Preview
    factory = RequestFactory()
    request = factory.get(f'/api/v1/audits/{audit.id}/export/preview/')
    request.user = user
    
    from rest_framework.test import force_authenticate
    force_authenticate(request, user=user)

    view = AuditExportPreviewView.as_view()
    response = view(request, audit_id=audit.id)
    
    if hasattr(response, 'render'):
        response.render()
    
    content = response.content.decode('utf-8')
    
    # 3. Assertions
    print("\n--- Assertions ---")
    
    # Check PASS Evidence Visible
    if "frontend-repo-PASS" in content:
        print("✅ PASS Evidence (frontend-repo-PASS) found in output")
    else:
        print("❌ PASS Evidence MISSING")
        
    # Check RAW DATA for PASS Evidence
    if "protected" in content:
        print("✅ RAW DATA for PASS Evidence found ('protected')")
    else:
        print("❌ RAW DATA for PASS Evidence MISSING")
        
    # Check FAIL Evidence Visible
    if "backend-repo-FAIL" in content:
        print("✅ FAIL Evidence (backend-repo-FAIL) found in output")
    else:
        print("❌ FAIL Evidence MISSING")

    # Check Summary Removed
    if "Compliance met across" in content:
        print("❌ PASS Summary ('Compliance met across') STILL PRESENT (Should be removed)")
    else:
        print("✅ PASS Summary REMOVED")
        
    # Check System Logs Label
    if "System Logs:" in content:
        print("✅ 'System Logs:' label found")
    else:
        print("❌ 'System Logs:' label MISSING")

    if response.status_code == 200:
        print("\n✅ API Response 200 OK")
    else:
        print(f"\n❌ API Failed with {response.status_code}")

try:
    verify_full_verbosity()
except Exception as e:
    print(f"Test Failed: {e}")
