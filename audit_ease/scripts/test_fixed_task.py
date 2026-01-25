
import os
import django
import sys
import logging

# Setup Django standalone
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

# Configure logging to see output
logging.basicConfig(level=logging.INFO)

from apps.audits.tasks import run_audit_task
from apps.audits.models import Audit

def test_task():
    # Use the same failing Audit ID
    audit_id = "33671c03-5b13-4c9d-849a-629cf097e544"
    print(f"Testing fix with Audit ID: {audit_id}")
    
    try:
        audit = Audit.objects.get(id=audit_id)
        print(f"Found Audit. Current Status: {audit.status}")
        
        # Reset status 
        audit.status = "PENDING"
        audit.save()
        
        print("Executing run_audit_task synchronously...")
        result = run_audit_task(audit_id)
        
        print("\n--- Result ---")
        print(result)
        
        # Refresh audit
        audit.refresh_from_db()
        print(f"Final Audit Status: {audit.status}")
        print(f"Score: {audit.score}")
        print(f"Reason: {audit.failure_reason if hasattr(audit, 'failure_reason') else 'N/A'}")
        
    except Audit.DoesNotExist:
        print("Audit not found! Did the DB change?")
    except Exception as e:
        print(f"Task Failed with Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_task()
