
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization, Membership
from apps.audits.models import Audit

User = get_user_model()

class ExportMessageTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="password")
        self.organization = Organization.objects.create(
            name="Free Org", 
            subscription_status=Organization.SUBSCRIPTION_STATUS_FREE,
            owner=self.user
        )
        # Owner is auto-added as ADMIN via signals
        self.client.force_authenticate(user=self.user)
        self.audit = Audit.objects.create(organization=self.organization, triggered_by=self.user)

    def test_export_forbidden_message(self):
        """Verify the 403 error message says 'Subscribe to download'."""
        # Test CSV export
        url = reverse('audits:audit-export-csv', args=[self.audit.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], "Subscribe to download")

        # Test PDF export
        url = reverse('audits:audit-export-pdf', args=[self.audit.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], "Subscribe to download")

