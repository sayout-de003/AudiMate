
import os
import django
import uuid

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "audit_ease.settings")
django.setup()

from apps.audits.logic import run_audit_sync
from apps.audits.models import Audit, Question, Evidence
from django.contrib.auth import get_user_model
from apps.integrations.models import Integration, Organization

User = get_user_model()

def verify_sync():
    print("Running synchronous audit verification...")
    
    # 1. Get a test user and org
    try:
        user = User.objects.first()
        if not user:
            print("No user found!")
            return
            
        org = Organization.objects.first()
        if not org:
            print("No organization found!")
            return
            
        print(f"Using User: {user.email}, Org: {org.name}")
        
    except Exception as e:
        print(f"Setup failed: {e}")
        return

    # 2. Create a new Audit
    audit = Audit.objects.create(
        organization=org,
        triggered_by=user,
        status='PENDING'
    )
    print(f"Created Audit ID: {audit.id}")
    
    # 3. List expected keys
    questions = Question.objects.all()
    print(f"Expecting checks for {questions.count()} questions.")
    
    # 4. Run Sync
    count = run_audit_sync(audit.id)
    print(f"Executed {count} checks.")
    
    # 5. Verify Results
    results = Evidence.objects.filter(audit=audit)
    print(f"Evidence count: {results.count()}")
    
    for r in results:
        print(f" - {r.question.key}: {r.status}")
        if r.status == 'FAIL':
             print(f"   Reason: {r.comment}")
        elif r.status == 'ERROR':
             print(f"   ERROR: {r.comment}")

verify_sync()
