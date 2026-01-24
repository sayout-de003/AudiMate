from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization
from apps.audits.models import Audit, Evidence, Question, AuditSnapshot

User = get_user_model()

class EvidenceCollectionTests(APITestCase):
    def setUp(self):
        # Create User first (needed for Organization owner)
        self.user = User.objects.create_user(email="test@example.com", password="password")
        
        # Create Organization
        self.organization = Organization.objects.create(
            name="Test Org", 
            subscription_status="PREMIUM",
            owner=self.user  # Required field
        )
        
        # Assign user to organization
        self.user.organization = self.organization
        self.user.save()
        
        # Authenticate
        self.client.force_authenticate(user=self.user)
        
        # Create Active Session (Audit)
        self.session = Audit.objects.create(
            organization=self.organization,
            triggered_by=self.user,
            status='RUNNING'
        )
        
        # Ensure Ad-hoc question exists (in case view creates it dynamically, but nice to have)
        Question.objects.get_or_create(key='adhoc_upload', defaults={'title': 'Ad-hoc', 'severity': 'LOW'})

    def test_upload_evidence_active_session(self):
        """
        Verify that evidence can be uploaded to an active session.
        """
        url = reverse('audits:evidence-upload')
        data = {
            'session_id': str(self.session.id),
            'evidence_type': 'log',
            'data': {'log_id': '12345', 'content': 'Error log content'}
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("successfully appended", response.data['message'])
        
        # Verify DB
        self.assertEqual(Evidence.objects.count(), 1)
        evidence = Evidence.objects.first()
        self.assertEqual(evidence.audit, self.session)
        self.assertEqual(evidence.raw_data['content']['log_id'], '12345')

    def test_upload_evidence_frozen_session(self):
        """
        Verify that evidence CANNOT be uploaded to a frozen session.
        """
        # Freeze session
        self.session.status = 'COMPLETED'
        self.session.save()
        
        url = reverse('audits:evidence-upload')
        data = {
            'session_id': str(self.session.id),
            'evidence_type': 'screenshot',
            'data': {'base64': '...'}
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Session is frozen", response.data['error'])
        
        # Verify DB
        self.assertEqual(Evidence.objects.count(), 0)

    def test_finalize_session(self):
        """
        Verify that a session can be finalized (frozen).
        """
        url = reverse('audits:session-finalize', args=[self.session.id])
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("now FROZEN", response.data['message'])
        
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, 'COMPLETED')
        self.assertIsNotNone(self.session.completed_at)

    def test_milestone_creation(self):
        """
        Verify that a milestone can be created.
        """
        url = reverse('audits:evidence-milestone')
        data = {
            'session_id': str(self.session.id),
            'title': 'Pre-Deployment Baseline',
            'description': 'Snapshot before release v2.0'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify DB
        self.assertEqual(AuditSnapshot.objects.count(), 1)
        snapshot = AuditSnapshot.objects.first()
        self.assertEqual(snapshot.name, 'Pre-Deployment Baseline')
        self.assertEqual(snapshot.audit, self.session)

    def test_legacy_evidence_create_frozen_check(self):
        """
        Verify that the legacy evidence creation endpoint naturally rejects frozen sessions too.
        """
        self.session.status = 'COMPLETED'
        self.session.save()
        
        # Create a question to link
        question = Question.objects.create(key='test_q', title='Test', severity='HIGH')
        
        url = reverse('audits:audit-evidence-create', args=[self.session.id])
        data = {
            'question_id': question.id,
            'status': 'FAIL',
            'raw_data': {},
            'comment': 'Manual finding'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Session is frozen", str(response.data))
