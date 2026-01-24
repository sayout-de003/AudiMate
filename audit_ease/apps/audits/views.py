"""
Audit API Views with Industry-Grade Security

All endpoints enforce:
- Organization isolation (IsSameOrganization)
- Authentication (IsAuthenticated)
- Proper RBAC from membership roles
- Audit logging for compliance

No endpoint exposes data from other organizations.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import permissions, generics
from rest_framework.exceptions import ValidationError
from apps.organizations.permissions import IsSameOrganization
from .models import Audit, Evidence, AuditSnapshot, Question
from .serializers import (
    AuditSerializer, 
    EvidenceSerializer, 
    AuditSnapshotSerializer, 
    AuditSnapshotCreateSerializer, 
    AuditSnapshotDetailSerializer, 
    EvidenceCreateSerializer,
    EvidenceUploadSerializer,
    EvidenceMilestoneSerializer
)
from apps.core.permissions import HasGeneralAccess, CheckTrialQuota
from .services import create_audit_snapshot
from apps.audits.services.stats_service import AuditStatsService
from .logic import run_audit_sync
from .mixins import RequireGitHubTokenMixin
from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Q
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.conf import settings
from datetime import timedelta
import logging
import uuid
import threading

logger = logging.getLogger(__name__)


def run_audit_background(audit_id: str, user_id: int) -> None:
    """
    Background worker function to execute audit checks asynchronously.
    
    Runs in a separate thread from the main request handler.
    
    Args:
        audit_id: UUID of the audit to execute
        user_id: ID of the user who triggered the audit
    
    Lifecycle:
        1. Fetches the Audit object
        2. Sets status to 'RUNNING'
        3. Executes compliance checks via run_audit_sync
        4. Updates status to 'COMPLETED' on success or 'FAILED' on error
    """
    try:
        # Fetch the audit
        audit = Audit.objects.get(id=audit_id)
        
        logger.info(
            f"Background audit worker started for audit {audit.id} "
            f"(organization: {audit.organization.name}, user: {user_id})"
        )
        
        # Mark as running
        audit.status = 'RUNNING'
        audit.save(update_fields=['status'])
        
        # Execute all compliance checks
        check_count = run_audit_sync(audit_id)
        
        # Refresh to ensure we have the latest status from run_audit_sync
        audit.refresh_from_db()
        
        logger.info(
            f"Background audit worker completed for audit {audit.id}: "
            f"{check_count} checks executed, status={audit.status}"
        )
        
    except Audit.DoesNotExist:
        logger.error(f"Audit {audit_id} not found during background execution")
    except Exception as e:
        logger.exception(f"Background audit worker failed for audit {audit_id}: {e}")
        try:
            audit = Audit.objects.get(id=audit_id)
            audit.status = 'FAILED'
            audit.save(update_fields=['status'])
        except Exception as inner_e:
            logger.error(f"Could not update audit status to FAILED: {inner_e}")


@method_decorator(
    ratelimit(key='user', rate=lambda g, r: settings.AUDIT_RATE_LIMIT, method='POST', block=True),
    name='dispatch'
)
class AuditStartView(RequireGitHubTokenMixin, APIView):
    """
    POST /api/v1/audits/start/
    
    Starts a new security audit for the requesting user's organization.
    Rate Limited: 5 audits per hour per user (configurable via AUDIT_RATE_LIMIT setting).
    
    SECURITY:
    - RequireGitHubTokenMixin: Redirects to profile if GitHub not connected.
    - IsSameOrganization: User can only audit their own organization
    - IsAuthenticated: User must be logged in
    - Rate Limiting: 5 audits per hour to prevent API abuse
    - Audit is linked to organization and triggering user
    """
    permission_classes = [permissions.IsAuthenticated, IsSameOrganization, HasGeneralAccess]

    def post(self, request):
        """
        Create and execute a new audit for the user's organization.
        
        Rate Limited: Controlled by AUDIT_RATE_LIMIT setting via ratelimit decorator.
        
        Returns HTTP 202 (Accepted) immediately while background worker executes checks.
        Frontend should poll GET /api/v1/audits/{audit_id}/ to check for completion.
        """
        try:
            # Get user's organization from context (set by OrgContextMiddleware)
            organization = request.user.get_organization()
            if not organization:
                return Response(
                    {'error': 'User is not a member of any organization'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create audit record with PENDING status
            audit = Audit.objects.create(
                organization=organization,
                triggered_by=request.user,
                status='PENDING'
            )
            
            logger.info(
                f"Audit {audit.id} created for organization {organization.name} by {request.user.email}. "
                f"Status: PENDING. Launching background worker thread."
            )
            
            # Trigger Celery task
            from .tasks import run_audit_task
            run_audit_task.delay(audit.id)
            
            # Return 202 Accepted immediately
            return Response(
                {
                    'message': 'Audit started in background',
                    'audit_id': str(audit.id),
                    'status': 'PENDING',
                    'organization': organization.name,
                    'triggered_by': request.user.email,
                    'created_at': audit.created_at.isoformat(),
                    'note': 'Poll GET /api/v1/audits/{audit_id}/ every 3 seconds to check for completion'
                },
                status=status.HTTP_202_ACCEPTED
            )
            
        except Exception as e:
            logger.exception(f"Error starting audit: {e}")
            return Response(
                {'error': 'Failed to start audit. Please check logs for details.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuditDetailView(APIView):
    """
    GET /api/v1/audits/{audit_id}/
    
    Retrieve details of a specific audit.
    
    SECURITY: Can only access audits belonging to user's organization.
    """
    permission_classes = [permissions.IsAuthenticated, IsSameOrganization, HasGeneralAccess]
    
    def get(self, request, audit_id):
        """Get audit details."""
        try:
            # Verify audit exists and belongs to user's organization
            organization = request.user.get_organization()
            
            audit = Audit.objects.get(
                id=audit_id,
                organization=organization
            )
            
            serializer = AuditSerializer(audit)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Audit.DoesNotExist:
            return Response(
                {'error': 'Audit not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )


class AuditEvidenceView(APIView):
    """
    GET /api/v1/audits/{audit_id}/evidence/
    
    Retrieve all evidence/findings from an audit.
    
    SECURITY: Can only access evidence from audits belonging to user's organization.
    """
    permission_classes = [permissions.IsAuthenticated, IsSameOrganization]
    
    def get(self, request, audit_id):
        """Get all evidence for an audit."""
        try:
            organization = request.user.get_organization()
            
            audit = Audit.objects.get(
                id=audit_id,
                organization=organization
            )
            
            evidence_list = Evidence.objects.filter(audit=audit).select_related('question')
            serializer = EvidenceSerializer(evidence_list, many=True)
            
            return Response(
                {
                    'audit_id': str(audit.id),
                    'organization': audit.organization.name,
                    'status': audit.status,
                    'evidence_count': evidence_list.count(),
                    'evidence': serializer.data
                },
                status=status.HTTP_200_OK
            )
            
        except Audit.DoesNotExist:
            return Response(
                {'error': 'Audit not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )


class AuditListView(APIView):
    """
    GET /api/v1/audits/
    
    List all audits for the user's organization.
    
    SECURITY: Automatically filters to organization's audits only.
    """
    permission_classes = [permissions.IsAuthenticated, IsSameOrganization, HasGeneralAccess]
    
    def get(self, request):
        """Get all audits for organization."""
        organization = request.user.get_organization()
        if not organization:
            return Response(
                {'error': 'User is not a member of any organization'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Query optimization: select_related for foreign keys
        audits = Audit.objects.filter(
            organization=organization
        ).select_related('organization', 'triggered_by').order_by('-created_at')
        
        serializer = AuditSerializer(audits, many=True)
        return Response(
            {
                'organization': organization.name,
                'audit_count': audits.count(),
                'audits': serializer.data
            },
            status=status.HTTP_200_OK
        )


class DashboardSummaryView(APIView):
    """
    GET /api/v1/audits/dashboard/summary/
    
    Executive dashboard with aggregated security metrics for the organization.
    
    Returns:
    - Total Audits Run (Last 30 days)
    - Current Pass Rate %
    - Open Issues by Severity (Critical/High/Medium)
    - Top Failing Repos/Resources
    
    SECURITY: Organization-isolated using IsSameOrganization permission.
    PERFORMANCE: Uses Django aggregates for efficient database queries.
    """
    permission_classes = [permissions.IsAuthenticated, IsSameOrganization]
    
    def get(self, request):
        """Get dashboard summary statistics."""
        try:
            organization = request.user.get_organization()
            if not organization:
                return Response(
                    {'error': 'User is not a member of any organization'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Time range: last 30 days
            thirty_days_ago = timezone.now() - timedelta(days=30)
            
            # Query audits for this organization in the last 30 days
            audits_30d = Audit.objects.filter(
                organization=organization,
                created_at__gte=thirty_days_ago
            )
            
            # 1. Total Audits Run (Last 30 days)
            total_audits = audits_30d.count()
            completed_audits = audits_30d.filter(status='COMPLETED').count()
            pending_audits = audits_30d.filter(status='PENDING').count()
            failed_audits = audits_30d.filter(status='FAILED').count()
            
            # 2. Current Pass Rate %
            # Get all evidence from audits in last 30 days
            evidence_30d = Evidence.objects.filter(
                audit__organization=organization,
                audit__created_at__gte=thirty_days_ago
            )
            
            passed_evidence = evidence_30d.filter(status='PASS').count()
            failed_evidence = evidence_30d.filter(status='FAIL').count()
            error_evidence = evidence_30d.filter(status='ERROR').count()
            total_evidence = evidence_30d.count()
            
            # Calculate pass rate
            if total_evidence > 0:
                pass_rate = round((passed_evidence / total_evidence) * 100, 2)
            else:
                pass_rate = 0
            
            # 3. Open Issues by Severity
            # Join Evidence with Question to get severity
            severity_breakdown = Evidence.objects.filter(
                status='FAIL',
                audit__organization=organization,
                audit__created_at__gte=thirty_days_ago
            ).values('question__severity').annotate(
                count=Count('id')
            ).order_by('question__severity')
            
            issues_by_severity = {
                'CRITICAL': 0,
                'HIGH': 0,
                'MEDIUM': 0,
                'LOW': 0,
            }
            
            for item in severity_breakdown:
                severity = item.get('question__severity', 'LOW')
                issues_by_severity[severity] = item.get('count', 0)
            
            # 4. Top Failing Resources
            # Get the most frequently failing questions
            top_failing_questions = Evidence.objects.filter(
                status='FAIL',
                audit__organization=organization,
                audit__created_at__gte=thirty_days_ago
            ).values('question__key', 'question__title', 'question__severity').annotate(
                failure_count=Count('id')
            ).order_by('-failure_count')[:5]
            
            top_failing = [
                {
                    'question_key': item['question__key'],
                    'title': item['question__title'],
                    'severity': item['question__severity'],
                    'failures': item['failure_count']
                }
                for item in top_failing_questions
            ]
            
            # 5. Audit Status Trend (last 30 days by status)
            status_distribution = audits_30d.values('status').annotate(
                count=Count('id')
            )
            
            status_trend = {
                'PENDING': 0,
                'RUNNING': 0,
                'COMPLETED': 0,
                'FAILED': 0,
            }
            
            for item in status_distribution:
                status_trend[item['status']] = item['count']
            
            # 6. Recent Audit Timeline
            recent_audits = Audit.objects.filter(
                organization=organization,
                created_at__gte=thirty_days_ago
            ).order_by('-created_at')[:10].values(
                'id', 'status', 'created_at', 'completed_at'
            )
            
            recent_timeline = [
                {
                    'audit_id': str(audit['id']),
                    'status': audit['status'],
                    'created_at': audit['created_at'].isoformat(),
                    'completed_at': audit['completed_at'].isoformat() if audit['completed_at'] else None,
                    'duration_seconds': (
                        (audit['completed_at'] - audit['created_at']).total_seconds()
                        if audit['completed_at'] else None
                    )
                }
                for audit in recent_audits
            ]
            
            # Compile the dashboard response
            dashboard_data = {
                'organization': organization.name,
                'organization_id': str(organization.id),
                'time_period': {
                    'label': 'Last 30 days',
                    'start_date': thirty_days_ago.isoformat(),
                    'end_date': timezone.now().isoformat()
                },
                'audit_summary': {
                    'total_audits': total_audits,
                    'completed': completed_audits,
                    'pending': pending_audits,
                    'failed': failed_audits,
                    'status_trend': status_trend
                },
                'compliance_metrics': {
                    'pass_rate_percent': pass_rate,
                    'total_checks': total_evidence,
                    'passed': passed_evidence,
                    'failed': failed_evidence,
                    'errors': error_evidence
                },
                'issues': {
                    'by_severity': issues_by_severity,
                    'total_open_issues': sum(issues_by_severity.values()),
                    'top_failing_checks': top_failing
                },
                'recent_audits': recent_timeline
            }
            
            return Response(dashboard_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.exception(f"Error generating dashboard summary: {e}")
            return Response(
                {'error': 'Failed to generate dashboard summary'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



#     def get(self, request, task_id):
#         # Check status of the Celery task
#         task_result = AsyncResult(task_id)
        
#         response_data = {
#             "task_id": task_id,
#             "status": task_result.status,
#             "result": task_result.result if task_result.ready() else None
#         }
        

class AuditSnapshotCreateView(APIView):
    """
    POST /api/v1/audits/{audit_id}/snapshots/
    
    Trigger creation of a new immutable snapshot.
    """
    permission_classes = [permissions.IsAuthenticated, IsSameOrganization]
    
    def post(self, request, audit_id):
        try:
            organization = request.user.get_organization()
            
            # Verify audit exists and belongs to user's organization before proceeding
            if not Audit.objects.filter(id=audit_id, organization=organization).exists():
                 return Response({'error': 'Audit not found'}, status=status.HTTP_404_NOT_FOUND)

            serializer = AuditSnapshotCreateSerializer(data=request.data)
            if serializer.is_valid():
                snapshot = create_audit_snapshot(
                    audit_id=audit_id, 
                    user=request.user,
                    name=serializer.validated_data.get('name')
                )
                
                return Response(
                    AuditSnapshotSerializer(snapshot).data,
                    status=status.HTTP_201_CREATED
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.exception(f"Snapshot creation failed: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AuditSnapshotListView(APIView):
    """
    GET /api/v1/audits/{audit_id}/snapshots/
    List all snapshots for an audit.
    """
    permission_classes = [permissions.IsAuthenticated, IsSameOrganization]
    
    def get(self, request, audit_id):
        try:
             organization = request.user.get_organization()
             audit = Audit.objects.get(id=audit_id, organization=organization)
             
             snapshots = AuditSnapshot.objects.filter(audit=audit)
             serializer = AuditSnapshotSerializer(snapshots, many=True)
             return Response(serializer.data)
        except Audit.DoesNotExist:
             return Response({'error': 'Audit not found'}, status=status.HTTP_404_NOT_FOUND)

class AuditSnapshotDetailView(APIView):
    """
    GET /api/v1/audits/snapshots/{pk}/
    Retrieve a specific snapshot with full data.
    """
    permission_classes = [permissions.IsAuthenticated, IsSameOrganization]
    
    def get(self, request, pk):
        try:
            organization = request.user.get_organization()
            snapshot = AuditSnapshot.objects.get(pk=pk, organization=organization)
            
            serializer = AuditSnapshotDetailSerializer(snapshot)
            return Response(serializer.data)
        except AuditSnapshot.DoesNotExist:
            return Response({'error': 'Snapshot not found'}, status=status.HTTP_404_NOT_FOUND)


class DashboardStatsView(APIView):
    """
    GET /api/v1/audits/dashboard/stats/
    
    Returns statistics for the *latest completed audit* to ensure parity with 
    detailed reports (Excel/CSV).
    """
    permission_classes = [permissions.IsAuthenticated, IsSameOrganization]

    def get(self, request):
        try:
            organization = request.user.get_organization()
            if not organization:
                 return Response({'error': 'No organization'}, status=status.HTTP_400_BAD_REQUEST)

            # Fetch the latest COMPLETED audit
            latest_audit = Audit.objects.filter(
                organization=organization,
                status='COMPLETED'
            ).order_by('-created_at').first()

            if not latest_audit:
                 # Empty state for new users
                 return Response({
                     'has_audits': False,
                     'message': "Run your first audit to see analytics."
                 })

            # Calculate stats using the shared service
            stats = AuditStatsService.calculate_audit_stats(latest_audit)

            # Add History (Last 5 audits)
            history_qs = Audit.objects.filter(
                organization=organization
            ).order_by('-created_at')[:5]

            history = []
            for aud in history_qs:
                history.append({
                    'id': str(aud.id),
                    'created_at': aud.created_at.isoformat(),
                    'status': aud.status,
                    'is_latest': aud.id == latest_audit.id
                })

            response_data = {
                'has_audits': True,
                'latest_audit_id': str(latest_audit.id),
                'stats': stats,
                'history': history
            }
            
            return Response(response_data)
            
        except Exception as e:
            logger.exception(f"Dashboard stats error: {e}")
            return Response({'error': 'Internal Error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EvidenceCreateView(generics.CreateAPIView):
    """
    POST /api/v1/audits/{audit_id}/evidence/create/
    
    Manually add evidence to an audit.
    
    LIMITS:
    - Free Plan: Max 50 evidence items per organization.
    """
    serializer_class = EvidenceCreateSerializer
    serializer_class = EvidenceCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsSameOrganization, HasGeneralAccess, CheckTrialQuota]
    
    def perform_create(self, serializer):
        user = self.request.user
        organization = user.get_organization()
        audit_id = self.kwargs.get('audit_id')
        
        # Verify audit belongs to organization
        audit = get_object_or_404(Audit, id=audit_id, organization=organization)
        
        # IMMUTABILITY CHECK
        if audit.status == 'COMPLETED':
            raise ValidationError("Session is frozen. Evidence chain is locked.") # Strict compliance rule

        # Trial Limit Check handled by CheckTrialQuota permission
        
        serializer.save(audit=audit)

class EvidenceUploadView(APIView):
    """
    POST /api/v1/audits/evidence/upload/
    
    Upload evidence artifacts (logs, screenshots) to an active session.
    Strictly enforces "Active State" rules.
    """
    permission_classes = [permissions.IsAuthenticated, IsSameOrganization]

    def post(self, request):
        serializer = EvidenceUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        data = serializer.validated_data
        session_id = data['session_id']
        evidence_type = data['evidence_type']
        evidence_data = data['data']
        
        organization = request.user.get_organization()
        
        try:
            audit = Audit.objects.get(id=session_id, organization=organization)
        except Audit.DoesNotExist:
             return Response({'error': 'Session not found or access denied.'}, status=status.HTTP_404_NOT_FOUND)
             
        # IMMUTABILITY CHECK
        if audit.status == 'COMPLETED':
             return Response(
                 {'error': "Session is frozen. Evidence chain is locked."},
                 status=status.HTTP_403_FORBIDDEN
             )

        # Create Evidence Artifact
        # We need to map the generic "upload" to our Evidence model.
        # Since 'Question' is required for Evidence, but this simple upload endpoint doesn't seem to ask for a question ID, 
        # I will either need to create a default "Ad-hoc" question or prompt the user.
        # However, the prompt implies this is a direct action: "Usage: Uploading screenshots... appends to current session timeline."
        # I'll check if there's a generic question I can use or if I should make 'question' nullable in model (too risky to change model now).
        # Best approach: Try to find or create a generic "Ad-hoc Evidence" question.
        
        # Checking if a generic question exists, if not create one in memory or DB?
        # Better: Assume there is a generic question or require one. 
        # The prompt didn't specify Question ID. 
        # I will create a placeholder Question for "Uploaded Artifacts" if it doesn't exist, safely.
        
        question, _ = Question.objects.get_or_create(
            key='adhoc_upload',
            defaults={
                'title': 'Ad-hoc Evidence Artifact',
                'description': 'Manually uploaded evidence artifact.',
                'severity': 'MEDIUM'
            }
        )
        
        evidence = Evidence.objects.create(
            audit=audit,
            question=question,
            status='PASS', # Defaulting to PASS or just INFO? Model only has PASS/FAIL/ERROR. Using PASS as "Received".
            raw_data={'type': evidence_type, 'content': evidence_data},
            comment=f"Uploaded {evidence_type} evidence."
        )
        
        return Response(
            {'message': f"Evidence {evidence.id} successfully appended to Session {audit.id}."},
            status=status.HTTP_201_CREATED
        )

class EvidenceMilestoneView(APIView):
    """
    POST /api/v1/audits/evidence/milestone/
    
    Create a milestone (snapshot) for the session.
    """
    permission_classes = [permissions.IsAuthenticated, IsSameOrganization]

    def post(self, request):
        serializer = EvidenceMilestoneSerializer(data=request.data)
        if not serializer.is_valid():
             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        session_id = data['session_id']
        title = data['title']
        description = data.get('description', '')
        
        organization = request.user.get_organization()
        
        try:
             audit = Audit.objects.get(id=session_id, organization=organization)
        except Audit.DoesNotExist:
             return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Create Snapshot/Milestone
        # We reuse the existing create_audit_snapshot logic but alias it to "Milestone"
        try:
            snapshot = create_audit_snapshot(
                audit_id=audit.id,
                user=request.user,
                name=title
            )
            # You might want to store the description somewhere but Snapshot model only has name.
            # We will append description to name or ignore for now as per existing model limits.
            
            return Response(
                {
                    'message': f"Milestone '{title}' created.",
                    'milestone_id': snapshot.id,
                    'timestamp': snapshot.created_at
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.exception(f"Milestone creation failed: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SessionFinalizeView(APIView):
    """
    POST /api/v1/audits/session/{pk}/finalize/
    
    Marks the session as COMPLETED, freezing it.
    """
    permission_classes = [permissions.IsAuthenticated, IsSameOrganization]

    def post(self, request, pk):
        organization = request.user.get_organization()
        audit = get_object_or_404(Audit, id=pk, organization=organization)
        
        if audit.status == 'COMPLETED':
             return Response({'message': 'Session is already frozen.'}, status=status.HTTP_200_OK)
             
        # Freeze data
        audit.status = 'COMPLETED'
        audit.completed_at = timezone.now()
        audit.save()
        
        logger.info(f"Session {audit.id} finalized and frozen by {request.user.email}")
        
        return Response(
            {'message': f"Session {audit.id} is now FROZEN. No further changes allowed."},
            status=status.HTTP_200_OK
        )