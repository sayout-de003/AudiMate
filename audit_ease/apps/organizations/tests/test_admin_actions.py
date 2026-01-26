
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from django.utils import timezone
from apps.organizations.models import Organization, Membership
from apps.organizations.admin import OrganizationAdmin, activate_subscription

User = get_user_model()

class MockSuperUser:
    def has_perm(self, perm, obj=None):
        return True

class AdminActionTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(email='admin@example.com', password='password')
        self.org = Organization.objects.create(
            name="Free Org",
            subscription_status=Organization.SUBSCRIPTION_STATUS_FREE,
            owner=self.user
        )

    def test_activate_subscription_action(self):
        """Test that the admin action correctly activates a subscription."""
        
        # Verify initial state
        self.assertEqual(self.org.subscription_status, 'free')
        self.assertIsNone(self.org.subscription_started_at)
        
        # Create request
        request = self.factory.get('/admin/')
        request.user = self.user
        
        # Add support for messages
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        # Call the action directly
        queryset = Organization.objects.filter(id=self.org.id)
        modeladmin = OrganizationAdmin(Organization, self.site)
        
        activate_subscription(modeladmin, request, queryset)
        
        # Verify updated state
        self.org.refresh_from_db()
        self.assertEqual(self.org.subscription_status, 'active')
        self.assertIsNotNone(self.org.subscription_started_at)
        
        # Check if timestamp is recent
        now = timezone.now()
        self.assertTrue((now - self.org.subscription_started_at).seconds < 10)

