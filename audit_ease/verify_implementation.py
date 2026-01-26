import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/sayantande/audit_full_app/audit_ease')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.audits.models import Audit, Evidence, Question
from utils.scoring import calculate_audit_score
from apps.organizations.models import Organization
from django.core.files.uploadedfile import SimpleUploadedFile

def verify_scoring():
    print("Verifying Scoring Logic...")
    
    # Setup dummy data
    try:
        org, _ = Organization.objects.get_or_create(name="Test Org")
        audit = Audit.objects.create(organization=org)
        
        q1 = Question.objects.create(key="test_crit", title="Critical Q", severity="CRITICAL")
        q2 = Question.objects.create(key="test_high", title="High Q", severity="HIGH")
        
        # Scenario 1: No failures (Score 100)
        score = calculate_audit_score(audit)
        print(f"Scenario 1 (No evidence): Score {score} (Expected 100)")
        assert score == 100
        
        # Scenario 2: 1 Critical Fail (-15)
        Evidence.objects.create(audit=audit, question=q1, status="FAIL")
        score = calculate_audit_score(audit)
        print(f"Scenario 2 (1 Critical Fail): Score {score} (Expected 85)")
        assert score == 85
        
        # Scenario 3: 1 Critical + 1 High Fail (-15 -10 = -25)
        Evidence.objects.create(audit=audit, question=q2, status="FAIL")
        score = calculate_audit_score(audit)
        print(f"Scenario 3 (1 Crit + 1 High Fail): Score {score} (Expected 75)")
        assert score == 75
        
        print("✅ Scoring verification passed!")
        
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
             
        # Check upload path logic indirectly or by checking the function location
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

if __name__ == "__main__":
    verify_scoring()
    verify_model_fields()
    verify_imports()
