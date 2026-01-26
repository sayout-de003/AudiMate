from django.test import RequestFactory
from unittest.mock import MagicMock
from apps.reports.views import AuditReportPDFView
from apps.audits.models import Audit, Evidence, Question
from apps.organizations.models import Organization
from django.contrib.auth import get_user_model
import os

def verify_pdf_view():
    print("Verifying AuditReportPDFView...")
    
    # Setup Data
    User = get_user_model()
    # Use email/password as established
    user, _ = User.objects.get_or_create(email="pdf_view_test@example.com", defaults={"password": "password"})
    org, _ = Organization.objects.get_or_create(name="PDF View Test Org", defaults={"owner": user})
    audit = Audit.objects.create(organization=org)
    
    # Questions
    q_crit, _ = Question.objects.get_or_create(key="crit_check_pdf", defaults={"title": "Critical PDF Check", "severity": "CRITICAL"})
    
    # Evidence
    Evidence.objects.filter(audit=audit).delete()
    Evidence.objects.create(audit=audit, question=q_crit, status="FAIL", status_state="OPEN")
    
    # Setup Request
    factory = RequestFactory()
    # Test HTML format first to check content easily
    request = factory.get(f'/api/v1/reports/{audit.id}/pdf/?format=html')
    request.user = user
    request.query_params = {'format': 'html', 'force': 'true'} # Force regen
    
    view = AuditReportPDFView()
    
    try:
        response = view.get(request, id=audit.id)
        
        print(f"Response Status Code: {response.status_code}")
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            print(f"Content-Type: {response.get('Content-Type')}")
            
            if "Critical PDF Check" in content:
                print("✅ Found check title in HTML.")
            else:
                print("❌ Check title NOT found in HTML.")
                
            if "DEBUG ERROR" in content:
                 print("❌ Found DEBUG ERROR in HTML.")
            else:
                 print("✅ No DEBUG ERROR found.")
                 
        else:
            print(f"❌ View failed. Status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

verify_pdf_view()
