
import os
import sys
import django
from django.conf import settings
from unittest.mock import MagicMock

# Setup Django standalone
sys.path.append('/Users/sayantande/audit_full_app/audit_ease')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from apps.reports.views import AuditReportPDFView
from apps.audits.models import Audit, Evidence
from apps.organizations.models import Organization
from django.contrib.auth import get_user_model
import uuid

def verify_view_direct():
    print("Verifying AuditReportPDFView.get logic directly...")
    
    # Setup Data
    User = get_user_model()
    # Create valid user/org to satisfy get_object_or_404
    email = f"test_direct_{uuid.uuid4()}@example.com"
    user = User.objects.create_user(email=email, password="password")
    org = Organization.objects.create(name="Direct Test Org", owner=user, subscription_status='active')
    
    # Ensure user.get_organization returns org (Mocking or ensure model works)
    # We will rely on model working since we created the org with owner=user.
    # But just in case, we can patch the user instance if needed.
    # Let's trust the DB relationship first.
    
    audit = Audit.objects.create(organization=org, score=90)
    
    # Create mock request
    request = MagicMock()
    request.user = user
    # request.user.get_organization.return_value = org # Mock the method just in case
    request.query_params = {'format': 'html'}
    request.build_absolute_uri.return_value = "http://localhost:8000/"
    
    # Instantiate View
    view = AuditReportPDFView()
    view.request = request
    
    print(f"Calling view.get with audit {audit.id}...")
    try:
        response = view.get(request, id=audit.id)
        
        print(f"Response Status: {response.status_code}")
        content = response.content.decode('utf-8')
        
        print(f"Content Length: {len(content)}")
        
        # Check for tags
        tags = ["{{ audit.organization.name }}", "{{ check.severity }}"]
        found = [t for t in tags if t in content]
        
        if found:
            print(f"❌ FAIL: Unrendered tags found: {found}")
            idx = content.find(found[0])
            print(f"Snippet: {content[idx-50:idx+50]}")
        else:
            print("✅ SUCCESS: No unrendered tags.")
            
        if "Direct Test Org" in content:
            print("✅ Organization name rendered correctly.")
        else:
            print("❌ Organization name NOT found.")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_view_direct()
