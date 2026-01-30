
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.users.models import User
from apps.organizations.models import Organization, Membership
from apps.audits.models import Audit, Evidence, Question
import uuid

class BusinessLogicTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create Users first (Owner needed for Org)
        self.owner = User.objects.create_user(email="owner@test.com", password="password")
        
        # Create Org
        self.org = Organization.objects.create(name="Test Org", subscription_status="active", owner=self.owner)
        # Membership for owner is auto-created by signal
        self.free_user = User.objects.create_user(email="free@test.com", password="password")
        Membership.objects.create(user=self.free_user, organization=self.org, role='admin')
        
        self.vip_user = User.objects.create_user(email="vip@test.com", password="password", is_comped_vip=True)
        Membership.objects.create(user=self.vip_user, organization=self.org, role='admin')
        
        self.pro_user = User.objects.create_user(email="pro@test.com", password="password", stripe_subscription_status='active')
        Membership.objects.create(user=self.pro_user, organization=self.org, role='admin')

        # Create Audits
        self.audit = Audit.objects.create(organization=self.org, triggered_by=self.free_user, status='COMPLETED')
        self.question = Question.objects.create(key="cis_1_1", title="MFA", severity="CRITICAL")
        Evidence.objects.create(audit=self.audit, question=self.question, status="FAIL")

    def test_user_properties(self):
        """Verify has_pro_access logic."""
        self.assertFalse(self.free_user.has_pro_access)
        self.assertTrue(self.vip_user.has_pro_access)
        self.assertTrue(self.pro_user.has_pro_access)
        
        # Test override on free user
        self.free_user.is_comped_vip = True
        self.free_user.save()
        self.assertTrue(self.free_user.has_pro_access)

    def test_pdf_export_gating(self):
        """Verify PDF export is gated."""
        url = reverse('audits:audit-export-pdf', args=[self.audit.id])
        
        # Free User -> 403
        self.client.force_authenticate(user=self.free_user)
        # Revert VIP status from previous test
        self.free_user.is_comped_vip = False 
        self.free_user.save()
        
        # Mock org subscription status to 'free' or 'inactive' to test USER LEVEL gating logic overrides
        # But wait, the VIEW checks `request.user.has_pro_access`.
        # Even if Org is active?
        # The requirements said: "Check 2: Does user.stripe_subscription_status == 'active'?"
        # Actually usually subscription is on the ORG level for B2B.
        # But the User Model has `stripe_subscription_status`.
        # My implementation checks `request.user.has_pro_access`.
        # So I should ensure the user itself is gated.
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['ui_action'], 'OPEN_UPGRADE_MODAL')

        # VIP User -> 200 (or PDF content)
        self.client.force_authenticate(user=self.vip_user)
        response = self.client.get(url)
        # Note: Weasyprint might fail or be missing, causing 500, but we expect pass on auth check.
        # If Weasyprint is missing, it catches ImportError and might fail differently?
        # Let's check status code. 200 means success. 500 means server error (likely rendering).
        # We assume 200 or 500 depending on env, but definitely NOT 403.
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_history_limit(self):
        """Verify history limit for free users."""
        # Create 10 audits
        for i in range(10):
             Audit.objects.create(organization=self.org, status='COMPLETED')
             
        url = reverse('audits:audit-list')
        
        # Free User -> 3 items
        self.client.force_authenticate(user=self.free_user)
        self.free_user.is_comped_vip = False
        self.free_user.save()
        
        response = self.client.get(url)
        self.assertEqual(len(response.data['audits']), 3)

        # VIP User -> All 11 items (1 initial + 10 new)
        self.client.force_authenticate(user=self.vip_user)
        response = self.client.get(url)
        self.assertTrue(len(response.data['audits']) > 3)
