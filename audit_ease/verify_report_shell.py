from django.test import RequestFactory
from unittest.mock import MagicMock
from apps.audits.api.views import AuditViewSet
from apps.audits.models import Audit, Evidence, Question
from apps.organizations.models import Organization
from django.contrib.auth import get_user_model
import os

def verify_report_generation():
    print("Verifying Report Generation...")
    
    # Setup Data
    User = get_user_model()
    # Use email/password as established in previous fixes
    user, _ = User.objects.get_or_create(email="report_test_shell@example.com", defaults={"password": "password"})
    org, _ = Organization.objects.get_or_create(name="Report Test Org Shell", defaults={"owner": user})
    audit = Audit.objects.create(organization=org)
    
    # Use update_or_create or get_or_create for questions to avoid unique key collisions
    q_crit, _ = Question.objects.get_or_create(key="crit_check_shell", defaults={"title": "Critical Check Shell", "severity": "CRITICAL", "description": "Desc"})
    q_pass, _ = Question.objects.get_or_create(key="pass_check_shell", defaults={"title": "Passing Check Shell", "severity": "HIGH", "description": "Desc"})
    
    # Create Evidence (Delete old for this audit first)
    Evidence.objects.filter(audit=audit).delete()
    
    # Fail Critical
    Evidence.objects.create(audit=audit, question=q_crit, status="FAIL", status_state="OPEN")
    # Pass High
    Evidence.objects.create(audit=audit, question=q_pass, status="PASS", status_state="FIXED")
    
    # Setup Request
    factory = RequestFactory()
    request = factory.get(f'/api/audits/{audit.id}/report/')
    request.user = user
    
    # Instantiate ViewSet
    view = AuditViewSet()
    view.request = request
    view.format_kwarg = None
    view.kwargs = {'pk': audit.id}
    view.action = 'report'
    
    # Mock
    view.get_object = MagicMock(return_value=audit)
    
    # Call report
    try:
        response = view.report(request, pk=audit.id)
        
        print(f"Response Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Report generated successfully (200 OK)")
            print(f"Content-Type: {response.get('Content-Type')}")
            if response.get('Content-Type') == 'application/pdf':
                print("✅ Content-Type is PDF")
            else:
                 print(f"❌ Content-Type mismatch: {response.get('Content-Type')}")
            
            # Optional: Check size
            if len(response.getvalue()) > 0:
                print(f"✅ PDF Size: {len(response.getvalue())} bytes")
                # Save it to check manually if desired (though I can't see it)
                # with open("debug_report.pdf", "wb") as f:
                #     f.write(response.getvalue())
            else:
                print("❌ PDF is empty")
        else:
            print(f"❌ Report generation failed. Status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Exception during report generation: {e}")
        import traceback
        traceback.print_exc()

verify_report_generation()
