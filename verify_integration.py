import os
import django
import sys

# Setup Django
sys.path.append('/Users/sayantande/audit_full_app/audit_ease')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from rest_framework.test import APIRequestFactory
from apps.users.models import User
from apps.organizations.models import Organization
from apps.integrations.models import Integration
from apps.integrations.serializers import IntegrationSerializer

# Bypass auditlog to avoid 'no such table' error in test script
try:
    from auditlog.registry import auditlog
    if auditlog.contains(User):
        auditlog.unregister(User)
    if auditlog.contains(Integration):
        auditlog.unregister(Integration)
except ImportError:
    pass

def verify():
    print("Setting up test data...")
    # Create User and Org
    user, _ = User.objects.get_or_create(email="test@example.com", defaults={'first_name': 'TestUser'})
    org, _ = Organization.objects.get_or_create(name="Test Org", owner=user)

    print("\n--- Test 1: Happy Path (Default Provider) ---")
    data = {
        'name': 'My GitHub',
        'external_id': '12345'
    }
    # Emulate request context
    class MockRequest:
        def __init__(self, user, org):
            self.user = user
            self.organization = org

    request = MockRequest(user, org)
    
    # Serializer with context
    serializer = IntegrationSerializer(data=data, context={'request': request})
    if serializer.is_valid():
        print("Serializer Valid.")
        # In ViewSet perform_create we pass additional data, but valid_data only has fields in serializer
        # provider defaults to 'github'
        print(f"Validated Data: {serializer.validated_data}")
        if serializer.validated_data.get('provider') == 'github':
             print("SUCCESS: Provider defaulted to 'github'")
        else:
             print(f"FAILURE: Provider is {serializer.validated_data.get('provider')}")
    else:
        print(f"FAILURE: {serializer.errors}")

    print("\n--- Test 2: Malicious Input (Provider = gitlab) ---")
    data_malicious = {
        'name': 'My GitLab',
        'external_id': '67890',
        'provider': 'gitlab'
    }
    serializer = IntegrationSerializer(data=data_malicious, context={'request': request})
    
    if serializer.is_valid():
        print("Serializer Valid (Unexpected if we want 400).")
        # If it is valid, check what the provider value is.
        # If it ignored 'gitlab' and set 'github', that matches "Strictly set provider='github'" 
        # but fails "Return 400 Bad Request".
        print(f"Validated Data: {serializer.validated_data}")
        if serializer.validated_data.get('provider') == 'github':
             print("WARNING: Input 'gitlab' was ignored and replaced with 'github'. check requirements.")
        else:
             print("FAILURE: Accepted 'gitlab'!")
    else:
        print("SUCCESS: Serializer rejected 'gitlab'")
        print(f"Errors: {serializer.errors}")

if __name__ == "__main__":
    verify()
