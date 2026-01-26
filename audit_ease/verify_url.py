import os
import sys
import django

sys.path.append('/Users/sayantande/audit_full_app')
sys.path.append('/Users/sayantande/audit_full_app/audit_ease')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.test import Client
from django.urls import reverse, resolve
from apps.audits.models import Evidence, Audit, Question
from apps.organizations.models import Membership
from django.contrib.auth import get_user_model

def verify_url_resolution():
    User = get_user_model()
    
    # Setup data
    user, _ = User.objects.get_or_create(email='url@test.com')
    from apps.organizations.models import Organization
    org = Organization.objects.first()
    if not org:
        org = Organization.objects.create(name="Test Org")
        
    audit = Audit.objects.create(organization=org, status='COMPLETED')
    question, _ = Question.objects.get_or_create(key='url_test')
    evidence = Evidence.objects.create(audit=audit, question=question, status='PASS')
    
    # Ensure membership for permission
    Membership.objects.get_or_create(user=user, organization=audit.organization, role='ADMIN')

    # Construct URL
    # Assuming the app_name is 'audits' and the path is included typically under /api/v1/audits/
    # But reverse() is the safest way to find what the actual URL is.
    try:
        url = reverse('audits:evidence-upload-screenshot', kwargs={'pk': evidence.id})
        print(f"Success: URL Reversed to: {url}")
    except Exception as e:
        print(f"Failure: Could not reverse URL: {e}")
        return

    # Resolve URL
    try:
        match = resolve(url)
        print(f"Success: URL Resolved to view: {match.func.view_class.__name__}")
    except Exception as e:
        print(f"Failure: Could not resolve URL {url}: {e}")
        return

    # Test Client Request (End-to-End)
    client = Client()
    # client.force_login(user) # Session auth won't work anymore for this view
    
    # Generate JWT
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)
    token = str(refresh.access_token)
    
    # Mock file
    from django.core.files.uploadedfile import SimpleUploadedFile
    f = SimpleUploadedFile("test.png", b"data", content_type="image/png")
    
    response = client.post(
        url, 
        {'file': f}, 
        format='multipart',
        HTTP_AUTHORIZATION=f'Bearer {token}'
    )
    print(f"Client Response Status: {response.status_code}")
    if response.status_code == 200:
        print("Success: Endpoint is reachable and working.")
    else:
        print(f"Failure: Endpoint returned {response.status_code}. Content: {response.content}")

if __name__ == "__main__":
    verify_url_resolution()
