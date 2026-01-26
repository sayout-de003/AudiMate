from apps.audits.models import Audit, Evidence, Question
from utils.scoring import calculate_audit_score
from apps.organizations.models import Organization
from django.contrib.auth import get_user_model
import sys

def verify_scoring():
    print("Verifying Scoring Logic...")
    
    # Setup dummy data
    try:
        User = get_user_model()
        user, _ = User.objects.get_or_create(email="test@example.com", defaults={"password": "password123"})
        org, _ = Organization.objects.get_or_create(name="Test Org", defaults={"owner": user})
        audit = Audit.objects.create(organization=org)
        
        # Use get_or_create to avoid uniqueness errors on re-runs
        q1, _ = Question.objects.get_or_create(key="test_crit", defaults={"title": "Critical Q", "severity": "CRITICAL"})
        q2, _ = Question.objects.get_or_create(key="test_high", defaults={"title": "High Q", "severity": "HIGH"})
        
        # Clear evidence
        Evidence.objects.filter(audit=audit).delete()
        
        # Scenario 1: No failures (Score 100)
        score = calculate_audit_score(audit)
        print(f"Scenario 1 (No evidence): Score {score} (Expected 100)")
        if score != 100:
            print("❌ Scenario 1 Failed")
        else:
            print("✅ Scenario 1 Passed")
        
        # Scenario 2: 1 Critical Fail (-15)
        Evidence.objects.create(audit=audit, question=q1, status="FAIL")
        score = calculate_audit_score(audit)
        print(f"Scenario 2 (1 Critical Fail): Score {score} (Expected 85)")
        if score != 85:
             print("❌ Scenario 2 Failed")
        else:
             print("✅ Scenario 2 Passed")
        
        # Scenario 3: 1 Critical + 1 High Fail (-15 -10 = -25)
        Evidence.objects.create(audit=audit, question=q2, status="FAIL")
        score = calculate_audit_score(audit)
        print(f"Scenario 3 (1 Crit + 1 High Fail): Score {score} (Expected 75)")
        if score != 75:
             print("❌ Scenario 3 Failed")
        else:
             print("✅ Scenario 3 Passed")
        
    except Exception as e:
        print(f"❌ Scoring verification failed: {e}")

def verify_model_fields():
    print("\nVerifying Model Fields...")
    try:
        e = Evidence()
        if hasattr(e, 'status_state'):
             print("✅ Evidence has 'status_state' field.")
        else:
             print("❌ Evidence MISSING 'status_state' field.")
             
        # Check upload path logic indirectly
        from apps.audits.models import evidence_upload_path
        print("✅ evidence_upload_path function exists.")

    except Exception as e:
        print(f"❌ Model verification failed: {e}")
        
def verify_imports():
    print("\nVerifying Imports...")
    try:
        import weasyprint
        import matplotlib
        from apps.audits.api.views import AuditViewSet
        print("✅ Imports successful.")
    except ImportError as e:
        print(f"❌ Import verification failed: {e}")

verify_scoring()
verify_model_fields()
verify_imports()
