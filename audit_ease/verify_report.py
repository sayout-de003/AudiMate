import os
import django
from django.conf import settings
from django.test import RequestFactory, override_settings
from unittest.mock import MagicMock
import sys

# Setup Django
sys.path.append('/Users/sayantande/audit_full_app/audit_ease')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.audits.api.views import AuditViewSet
from apps.audits.models import Audit, Evidence, Question
from apps.organizations.models import Organization
from django.contrib.auth import get_user_model

def verify_report_generation():
    print("Verifying Report Generation...")
    
    # Setup Data
    User = get_user_model()
    try:
        user, _ = User.objects.get_or_create(email="report_test@example.com", defaults={"password": "password"})
        org, _ = Organization.objects.get_or_create(name="Report Test Org", defaults={"owner": user})
        audit = Audit.objects.create(organization=org)
        
        # Create Questions
        q_crit = Question.objects.create(key="crit_check", title="Critical Check", severity="CRITICAL")
        q_pass = Question.objects.create(key="pass_check", title="Passing Check", severity="HIGH")
        
        # Create Evidence
        # Fail Critical
        Evidence.objects.create(audit=audit, question=q_crit, status="FAIL")
        # Pass High
        Evidence.objects.create(audit=audit, question=q_pass, status="PASS")
        
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
        
        # Mock get_object to avoid permissions/queryset hassle in standalone script if needed
        # But since we set request.user, it might work if permission classes run. 
        # AuditViewSet uses IsSameOrganization which checks request.user.get_organization().
        # We might need to mock get_organization on user or ensure it works.
        # Simpler: just set view.get_object = MagicMock(return_value=audit)
        view.get_object = MagicMock(return_value=audit)
        
        # Call report
        response = view.report(request, pk=audit.id)
        
        print(f"Response Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Report generated successfully (200 OK)")
            print(f"Content-Type: {response['Content-Type']}")
            if response['Content-Type'] == 'application/pdf':
                print("✅ Content-Type is PDF")
            else:
                 print(f"❌ Content-Type mismatch: {response['Content-Type']}")
        else:
            print(f"❌ Report generation failed. Status: {response.status_code}")
            if hasattr(response, 'data'):
                print(f"Error Data: {response.data}")

    except Exception as e:
        print(f"❌ Exception during verification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_report_generation()
