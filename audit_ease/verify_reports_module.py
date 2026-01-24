import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.http import StreamingHttpResponse
from apps.audits.views_export import export_audit_csv_streaming as export_audit_csv
from apps.reports.services import generate_audit_pdf
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory
from apps.audits.models import Audit, Evidence, Question
from apps.organizations.models import Organization
from django.contrib.auth import get_user_model

User = get_user_model()

def verify_csv_export():
    print("Verifying CSV Export...")
    # This is a static analysis check mainly, preventing actual DB hit if possible, 
    # but we can try to call it if we mock or have data.
    # Let's inspect the function code object or return type if we can run it.
    
    # Check imports in views_export.py
    import apps.audits.views_export as ve
    if not hasattr(ve, 'StreamingHttpResponse'):
        print("FAIL: StreamingHttpResponse not imported in views_export.py")
        return

    print("PASS: StreamingHttpResponse is used.")

def verify_pdf_generation():
    print("Verifying PDF Generation...")
    from django.template.loader import render_to_string
    from django.utils import timezone
    
    # Mock Objects
    class MockOrg:
        name = "Test Org"
    
    class MockAudit:
        id = "123"
        organization = MockOrg()
        score = 95
        
    class MockQuestion:
        title = "Test Question"
        key = "test_key"
        severity = "HIGH"
        
    class MockFinding:
        question = MockQuestion()
        status = "FAIL"
        comment = "Test Comment"
        created_at = timezone.now()
        
    audit = MockAudit()
    findings = [MockFinding()]
    
    try:
        context = {
            'audit': audit,
            'findings': findings,
            'report_date': timezone.now()
        }
        # Render HTML to check for template errors
        html = render_to_string('reports/audit_report.html', context)
        print("PASS: Template rendered successfully.")
        
        # Check for critical CSS
        if "@page" not in html:
            print("FAIL: @page CSS missing.")
        if "evidence-table" not in html:
            print("FAIL: evidence-table class missing.")
            print("DEBUG: Rendered HTML snippet:")
            print(html[:1000]) # Print first 1000 chars
            print("..." * 5)
            print(html[-1000:]) # Print last 1000 chars
            
    except Exception as e:
        print(f"FAIL: Template rendering failed: {e}")

if __name__ == "__main__":
    verify_csv_export()
    verify_pdf_generation()
