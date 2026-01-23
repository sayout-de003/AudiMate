from auditlog.registry import auditlog
from apps.organizations.models import Organization
from apps.users.models import User

def register_models():
    """
    Register models for Audit Logging.
    This function should be called when the app is ready.
    """
    # Track Organization changes (name, slug, subscription status, etc.)
    # We exclude 'updated_at' to reduce noise if that's the only change.
    auditlog.register(Organization, exclude_fields=['updated_at'])

    # Track User changes
    auditlog.register(User, exclude_fields=['last_login', 'date_joined'])
