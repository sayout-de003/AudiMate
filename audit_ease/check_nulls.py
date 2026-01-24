import os
import sys
import django

# Add the project directory to sys.path
sys.path.append(os.getcwd())

# Use the correct settings module as seen in manage.py
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from apps.audits.models import Audit
from apps.integrations.models import Integration

def check_nulls():
    audit_count = Audit.objects.filter(organization__isnull=True).count()
    integration_count = Integration.objects.filter(organization__isnull=True).count()
    
    print(f"Audits with null organization: {audit_count}")
    print(f"Integrations with null organization: {integration_count}")

if __name__ == "__main__":
    check_nulls()
