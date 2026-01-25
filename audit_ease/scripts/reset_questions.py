
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "audit_ease.settings")
django.setup()

from apps.audits.models import Question

def force_reset():
    print("Deleting ALL questions...")
    Question.objects.all().delete()
    print("All questions deleted. User 'loaddata' to re-import.")

force_reset()
