
from apps.audits.models import Audit, Evidence
from apps.organizations.models import Organization, Membership
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from apps.audits.views_export import AuditExportPreviewView, AuditExportPDFView
import uuid
import json

User = get_user_model()
from apps.organizations.models import Organization, Membership
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from apps.audits.views_export import AuditExportPreviewView, AuditExportPDFView
from apps.reports.views import AuditReportPDFView
import uuid
import json

User = get_user_model()

def verify_audit_report():
    print("Verifying Audit Report Generation (Legacy Endpoint)...")
    
    # 1. Setup Data
    email = f"test_auditor_{uuid.uuid4()}@example.com"
    user = User.objects.create_user(email=email, password="password")
    
    org = Organization.objects.create(
        name="Test Corp Security",
        subscription_status='active',
        owner=user
    )
    
    audit = Audit.objects.create(
        organization=org,
        score=85
    )
    
    # Create Evidence (Fail)
    fail_evidence = Evidence.objects.create(
        audit=audit,
        status='FAIL',
        raw_data={
            "repo_name": "test-repo-backend", 
            "branch": "main"
        },
        question_id=1  # Assuming fixture data exists or create mock question is needed. 
        # Since question is foreign key, we need a question.
    )
    # We strip question relation for this test OR need to mock it if DB is empty.
    # Let's check if we can create a mock question if needed, or rely on existing check logic which accesses question.key
    # Ideally we'd create a question too, but let's see if we can patch or if we need to Mock.
    # Actually, let's create a dummy question if possible.
    
    from apps.audits.models import Question
    question, created = Question.objects.get_or_create(
        key="BR_01",
        defaults={
            "title": "Branch Protection",
            "description": "Main branch must be protected",
            "severity": "HIGH"
        }
    )
    fail_evidence.question = question
    fail_evidence.save()
    
    # Create Evidence (Pass)
    pass_evidence = Evidence.objects.create(
        audit=audit, 
        status='PASS', 
        question=question,
        raw_data={"repo_name": "frontend-repo"}
    )

    # 2. Test Preview View (Using AuditExportPreviewView from apps.audits.views_export)
    print("Testing AuditExportPreviewView...")
    
    factory = RequestFactory()
    # URL doesn't matter much for as_view call but good to be consistent
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
    
    # Check Organization Name
    if "Test Corp Security" in content:
        print("✅ Organization Name found")
    else:
        print("❌ Organization Name MISSING")
        
    # Check Repository Name (Affected Resources)
    if "test-repo-backend" in content:
        print("✅ Repository Name (test-repo-backend) found in Affected Resources")
    else:
        print("❌ Repository Name MISSING")

    # Check Severity
    if "HIGH" in content:
        print("✅ Severity HIGH found")
    else:
        print("❌ Severity MISSING")

    # Check Pass Count logic
    # We look for "Compliance met across"
    if "Compliance met across" in content:
        print('✅ "Compliance met across" text found')
    else:
        print('❌ "Compliance met across" text MISSING')
        
    # Check CSS for Print
    if "@media print" in content:
        print("✅ @media print CSS block found")
    else:
        print("❌ @media print CSS MISSING")
        
    if "display: block !important;" in content and "json-logs" in content:
        print("✅ Print visibility rules found")

    # Check for UNRENDERED tags
    unrendered_tags = ["{{ check.severity }}", "{{ finding.remediation }}", "{{ audit.organization.name }}"]
    found_unrendered = [tag for tag in unrendered_tags if tag in content]
    
    if found_unrendered:
        print(f"❌ FAIL: Found unrendered tags: {found_unrendered}")
        # Print snippet context
        idx = content.find(found_unrendered[0])
        print(f"Context: {content[idx-50:idx+50]}")
    else:
        print("✅ No unrendered tags found.")

    if response.status_code == 200:
        print("\n✅ API Response 200 OK")
    else:
        print(f"\n❌ API Failed with {response.status_code}")

try:
    verify_audit_report()
except Exception as e:
    print(f"Test Failed: {e}")
