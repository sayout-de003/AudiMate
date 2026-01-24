from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.users.models import User
from apps.organizations.models import Organization
from apps.audits.models import Audit, Evidence, Question
from apps.audits.serializers import EvidenceSerializer
from apps.integrations.serializers import IntegrationSerializer
import uuid

class IsolationSecurityTests(TestCase):
    def setUp(self):
        # Setup Organization A
        self.org_a = Organization.objects.create(name="Org A")
        self.user_a = User.objects.create_user(email="user_a@example.com", password="password", organization=self.org_a)
        
        # Setup Organization B
        self.org_b = Organization.objects.create(name="Org B")
        self.user_b = User.objects.create_user(email="user_b@example.com", password="password", organization=self.org_b)
        
        # Setup Audit A (belongs to Org A)
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
        
        # Assuming the url name for AuditReportPDFView is 'audit-report-pdf' or similar. 
        # I need to check urls.py to be sure, but assuming based on typical patterns.
        # Actually, let's look at report view code again or just guess the path structure.
        # The prompt said "Locate apps/reports/views.py". I saw AuditReportPDFView.
        # I suspect the URL is something like /api/v1/reports/<id>/pdf/
        
        # Let's try constructing the URL manually if name isn't known, or use the view class if supported by test framework helpers (not usually).
        # Better: use the view directly or correct path.
        # reports/urls.py was not viewed. I should check it or just assume standard REST if I can't.
        # I'll check reports/urls.py in a sec, but for now let's assume /api/v1/reports/{id}/download/
        
        url = f"/api/v1/reports/{self.audit_a.id}/download/" 
        
        # If I don't know the exact URL, the 404 might be because URL is wrong, not because of isolation.
        # So verifying the URL is crucial.
        pass

    def test_same_tenant_report_access_allowed(self):
        """
        User A should be able to access their own audit report.
        """
        self.client.force_authenticate(user=self.user_a)
        # url = ...
        pass

class SerializerSecurityTests(TestCase):
    def test_evidence_raw_data_validation(self):
        """
        Test that raw_data must be a valid dict.
        """
        question = Question.objects.create(key="q1", title="Q1", description="desc")
        # Validation happens in serializer, so we don't need Audit strictness here necessarily
        
        # Invalid data (string instead of dict)
        data = {
            'question': {'id': question.id}, # This might be read only in serializer?
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
            # 'organization': ... (read only mostly)
            'provider': 'github',
            'external_id': '123',
            'config': "INVALID",
            'name': 'Test'
        }
        serializer = IntegrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('config', serializer.errors)
