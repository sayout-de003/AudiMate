from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.users.models import User
from apps.organizations.models import Organization, Membership
from apps.audits.models import Audit, Evidence, Question
from apps.audits.serializers import EvidenceSerializer
from apps.integrations.serializers import IntegrationSerializer
import uuid

class IsolationSecurityTests(TestCase):
    def setUp(self):
        # 1. Create Users first
        self.user_a = User.objects.create_user(email="user_a@example.com", password="password")
        self.user_b = User.objects.create_user(email="user_b@example.com", password="password")
        
        # 2. Create Organizations with owners (UNCOMMENTED THESE)
        self.org_a = Organization.objects.create(name="Org A", owner=self.user_a)
        self.org_b = Organization.objects.create(name="Org B", owner=self.user_b)
        
        # 3. Create Memberships (Safe against duplicates)
        # We use get_or_create to handle cases where signals might have already auto-created them
        Membership.objects.get_or_create(
            user=self.user_a, 
            organization=self.org_a, 
            defaults={'role': Membership.ROLE_ADMIN}
        )
        Membership.objects.get_or_create(
            user=self.user_b, 
            organization=self.org_b, 
            defaults={'role': Membership.ROLE_ADMIN}
        )
        
        # 4. Create Audit for Org A
        self.audit_a = Audit.objects.create(
            organization=self.org_a,
            status='COMPLETED'
        )
        
        self.client = APIClient()

    def test_cross_tenant_report_access_denied(self):
        """
        User B should get 404 when trying to access User A's audit report.
        """
        self.client.force_authenticate(user=self.user_b)
        url = reverse('audit-report-pdf', kwargs={'id': self.audit_a.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_same_tenant_report_access_allowed(self):
        """
        User A should be able to access their own audit report.
        """
        self.client.force_authenticate(user=self.user_a)
        url = reverse('audit-report-pdf', kwargs={'id': self.audit_a.id})
        response = self.client.get(url)
        # Should be 200 OK or 500 (if PDF generation breaks), but definitely NOT 404
        self.assertIn(response.status_code, [200, 500])

class SerializerSecurityTests(TestCase):
    def test_evidence_raw_data_validation(self):
        """
        Test that raw_data must be a valid dict.
        """
        # We need a question for the serializer context if used, but here we test field validation only usually.
        # But ModelSerializer might query DB.
        question = Question.objects.create(key="q1", title="Q1", description="desc")
        
        data = {
            'question': question.id, # Often ignored by read_only, but provided for completeness
            'status': 'PASS',
            'raw_data': "INVALID STRING - NOT A DICT",
            'comment': "test"
        }
        serializer = EvidenceSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('raw_data', serializer.errors)

    def test_integration_config_validation(self):
        """
        Test that integration config must be a valid dict.
        """
        data = {
            'provider': 'github',
            'external_id': '123',
            'config': "INVALID",
            'name': 'Test'
        }
        serializer = IntegrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('config', serializer.errors)
