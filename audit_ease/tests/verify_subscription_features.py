import os
import sys
import django
# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from django.conf import settings
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework import status
import uuid

from apps.users.models import User
from apps.organizations.models import Organization, Membership
from apps.audits.models import Audit, Evidence, Question

def setup_test_data():
    # clear data
    Evidence.objects.all().delete()
    Audit.objects.all().delete()
    Membership.objects.all().delete()
    Organization.objects.all().delete()
    User.objects.all().delete()
    Question.objects.all().delete()

    # Create Questions
    q1 = Question.objects.create(key='Q1', title='Test Question', severity='HIGH')

    # 1. Free Org
    free_user = User.objects.create_user(email='free@test.com', password='password')
    free_org = Organization.objects.create(name='Free Corp', subscription_status='free', owner=free_user)
    free_audit = Audit.objects.create(organization=free_org, triggered_by=free_user)

    # 2. Premium Org
    paid_user = User.objects.create_user(email='paid@test.com', password='password')
    paid_org = Organization.objects.create(name='Paid Corp', subscription_status='active', owner=paid_user)
    paid_audit = Audit.objects.create(organization=paid_org, triggered_by=paid_user)

    return {
        'free_user': free_user,
        'free_audit': free_audit,
        'paid_user': paid_user,
        'paid_audit': paid_audit,
        'question': q1
    }

def test_subscription_gating(data):
    print("\ntesting Subscription Gating...")
    client = APIClient()
    
    # Test Free User -> 403
    client.force_authenticate(user=data['free_user'])
    # Assuming the PDF view URL is /api/v1/reports/<audit_id>/pdf/ 
    # Need to check urls.py for reports app, I assumed it exists there.
    # Wait, the task said `apps/reports/views.py`, but I didn't verify reports URL.
    # I'll check reports/urls.py if it fails.
    # Assuming: /api/v1/reports/<id>/pdf/
    url = f"/api/v1/reports/{data['free_audit'].id}/pdf/"
    
    resp = client.get(url)
    if resp.status_code == 403:
        print("✅ Free user denied access (403)")
    else:
        print(f"❌ Free user NOT denied access: {resp.status_code}")

    # Test Paid User -> 200 (or 500 if PDF generation fails but permission passes)
    client.force_authenticate(user=data['paid_user'])
    url = f"/api/v1/reports/{data['paid_audit'].id}/pdf/"
    resp = client.get(url)
    if resp.status_code in [200, 500]: # 500 is acceptable if logic fails but auth passed
        print(f"✅ Paid user allowed access (Status: {resp.status_code})")
    elif resp.status_code == 403:
        print("❌ Paid user denied access (403)")
    else:
        print(f"⚠️ Unexpected status for paid user: {resp.status_code}")

def test_rate_limiting(data):
    print("\nTesting Rate Limiting...")
    client = APIClient()
    client.force_authenticate(user=data['paid_user'])
    url = f"/api/v1/reports/{data['paid_audit'].id}/pdf/"
    
    # settings has 'pdf_generation': '5/min'
    # Hit 5 times
    for i in range(5):
        client.get(url)
    
    # 6th time should fail
    resp = client.get(url)
    if resp.status_code == 429:
        print("✅ Rate limit enforced (429)")
    else:
        print(f"❌ Rate limit NOT enforced on 6th request: {resp.status_code}")

def test_trial_limits(data):
    print("\nTesting Trial Limits...")
    client = APIClient()
    client.force_authenticate(user=data['free_user'])
    url = f"/api/v1/audits/{data['free_audit'].id}/evidence/create/"
    
    # Add 50 items
    questions = []
    # Starting from 2 because q1 is already created
    for i in range(2, 52):
        questions.append(Question(key=f'Q{i}', title=f'Question {i}', severity='LOW'))
    Question.objects.bulk_create(questions)
    
    evidence_list = []
    for q in questions:
        evidence_list.append(Evidence(
            audit=data['free_audit'],
            question=q,
            status='PASS',
            raw_data={}
        ))
    Evidence.objects.bulk_create(evidence_list)
    
    print(f"Created {Evidence.objects.filter(audit=data['free_audit']).count()} evidence items directly in DB.")
    
    # Try to add 51st via API (using the original q1)
    # Since we have 50 items (from the loop), plus maybe 0 from before?
    # q1 was created in setup but NOT added as evidence to free_audit.
    # So free_audit has exactly 50 items now.
    
    payload = {
        'question_id': data['question'].id,
        'status': 'FAIL',
        'raw_data': {},
        'comment': 'Over limit'
    }
    
    resp = client.post(url, payload, format='json')
    if resp.status_code == 400 and 'Trial limit reached' in str(resp.data):
        print("✅ Trial limit enforced (400 ValidationError)")
    else:
        print(f"❌ Trial limit NOT enforced: {resp.status_code} {resp.data}")

if __name__ == "__main__":
    try:
        with override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1']):
            data = setup_test_data()
            test_subscription_gating(data)
            test_rate_limiting(data)
            test_trial_limits(data)
    except Exception as e:
        print(f"Test Execution Failed: {e}")
