import os
import django
import sys
import json
from unittest.mock import MagicMock

# Setup Django
sys.path.append('/Users/sayantande/audit_full_app/audit_ease')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from apps.audits.models import Audit, Evidence, Question
from apps.organizations.models import Organization
from django.contrib.auth import get_user_model
from apps.audits.views_export import AuditExportPDFView

def verify_pdf_view():
    print("🚀 Verifying AuditExportPDFView (WeasyPrint)...")
    
    User = get_user_model()
    # Create User & Org
    user, _ = User.objects.get_or_create(email="pdf_tester@example.com", defaults={"password": "password"})
    org, _ = Organization.objects.get_or_create(name="PDF Test Org", defaults={"owner": user, "subscription_status": "active"})
    
    # Create Audit
    audit = Audit.objects.create(organization=org, triggered_by=user, status='COMPLETED')
    
    # Create Questions & Evidence
    # 1. Critical Failure with JSON
    q1, _ = Question.objects.get_or_create(key="cis_1_1", defaults={"title": "MFA Enforced", "severity": "CRITICAL", "description": "MFA must be enabled."})
    Evidence.objects.create(
        audit=audit, 
        question=q1, 
        status="FAIL", 
        raw_data={"org": "my-org", "mfa_enabled": False, "admins_without_mfa": ["alice", "bob"]},
        comment="User alice and bob do not have MFA."
    )
    
    # 2. High Faliure with Screenshot (Mock)
    q2, _ = Question.objects.get_or_create(key="cis_2_1", defaults={"title": "Secret Scanning", "severity": "HIGH", "description": "Secrets detected."})
    # We won't actually create a file, just simulate the object if we can, or just leave screenshot null to test JSON/Null path.
    # Let's test the deduplication logic: 2 findings for same rule?
    q3, _ = Question.objects.get_or_create(key="cis_4_1", defaults={"title": "Branch Protection", "severity": "HIGH", "description": "Branch protection missing."})
    Evidence.objects.create(
        audit=audit, 
        question=q3, 
        status="FAIL", 
        raw_data={"repo_name": "repo-A", "protection": False},
        comment="Repo A is unprotected."
    )
    Evidence.objects.create(
        audit=audit, 
        question=q3, 
        status="FAIL", 
        raw_data={"repo_name": "repo-B", "protection": False},
        comment="Repo B is unprotected."
    )
    
    # 3. Passing Check
    q4, _ = Question.objects.get_or_create(key="cis_5_1", defaults={"title": "Code Owners", "severity": "LOW"})
    Evidence.objects.create(audit=audit, question=q4, status="PASS", raw_data={"repo_name": "repo-C"})

    # Test View
    factory = RequestFactory()
    request = factory.get(f'/api/audits/{audit.id}/export/pdf/')
    request.user = user
    request.build_absolute_uri = MagicMock(return_value="http://testserver/") # for WeasyPrint base_url
    
    view = AuditExportPDFView.as_view()
    response = view(request, audit_id=audit.id)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        content_type = response.get('Content-Type', '')
        print(f"Content-Type: {content_type}")
        
        if content_type == 'application/pdf':
            output_path = f"verify_output_{audit.id}.pdf"
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"✅ PDF generated and saved to: {output_path}")
            print("Please perform visual inspection if possible.")
        else:
            print("❌ Response is not PDF.")
            print(response.content[:500])
    else:
        print(f"❌ Failed. Status: {response.status_code}")
        if hasattr(response, 'data'):
            print(response.data)
        else:
             print(response.content[:500])

if __name__ == "__main__":
    verify_pdf_view()
