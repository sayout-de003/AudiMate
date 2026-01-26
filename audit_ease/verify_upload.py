import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/sayantande/audit_full_app')
# Also add the current directory just in case
sys.path.append('/Users/sayantande/audit_full_app/audit_ease')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from apps.audits.models import Evidence, Audit, Question
from apps.organizations.models import Organization
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from apps.audits.views import EvidenceScreenshotUploadView

def setup_test_data():
    # Get or create org
    org = Organization.objects.first()
    if not org:
        print("No organization found.")
        return None

    # Get or create audit
    audit = Audit.objects.create(organization=org, status='RUNNING')
    
    # Get or create question
    question, _ = Question.objects.get_or_create(key='test_check', defaults={'title': 'Test Check', 'severity': 'HIGH'})
    
    # Create evidence with Logs but NO screenshot
    evidence = Evidence.objects.create(
        audit=audit, 
        question=question, 
        status='FAIL', 
        raw_data={'error': 'test error', 'details': 'failed verification'},
        comment='Test evidence'
    )
    return evidence

def test_upload(evidence):
    # Simulate a file upload
    file_content = b'fake image content'
    uploaded_file = SimpleUploadedFile("test_screenshot.png", file_content, content_type="image/png")
    
    factory = RequestFactory()
    url = f'/api/v1/audits/evidence/{evidence.id}/upload_screenshot/'
    request = factory.post(url, {'file': uploaded_file}, format='multipart')
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    # Create or get a user
    user, created = User.objects.get_or_create(email='test@example.com', defaults={'username': 'testuser'})
    
    # Ensure membership
    from apps.organizations.models import Membership
    Membership.objects.get_or_create(user=user, organization=evidence.audit.organization, role='ADMIN')
    
    # Attach real user to request
    request.user = user
    request._dont_enforce_csrf_checks = True
    
    view = EvidenceScreenshotUploadView.as_view()
    response = view(request, pk=evidence.id)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Data: {response.data}")
    
    # Reload evidence
    evidence.refresh_from_db()
    if evidence.screenshot:
        print(f"Success: Screenshot saved at {evidence.screenshot.name}")
    else:
        print("Failure: Screenshot not saved")

if __name__ == "__main__":
    evidence = setup_test_data()
    if evidence:
        print(f"Testing with Evidence ID: {evidence.id}")
        test_upload(evidence)
