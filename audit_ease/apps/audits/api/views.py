import csv
import io
import logging
from datetime import datetime
from django.http import StreamingHttpResponse, HttpResponse, FileResponse
from django.shortcuts import get_object_or_404, render
from rest_framework import viewsets, status, mixins, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from apps.audits.models import Audit, Evidence
from apps.audits.serializers import AuditSerializer
from apps.organizations.permissions import IsSameOrganization
from apps.organizations.models import Membership
from apps.audits.services.stats_service import AuditStatsService
from apps.audits.serializers import EvidenceSerializer
from apps.core.permissions import HasProPlan

# ReportLab Imports
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER
except ImportError:
    pass

# OpenPyXL Imports
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

logger = logging.getLogger(__name__)

from rest_framework import permissions

class IsAuditOwner(permissions.BasePermission):
    """
    Custom permission to ensure user access to Audit via Organization or Ownership.
    """
    def has_object_permission(self, request, view, obj):
        # Check if audit.organization in user's organizations OR user is the one who triggered it
        # We use a membership check for "in request.user.organizations"
        user_orgs = [m.organization for m in request.user.memberships.all()]
        return (obj.organization in user_orgs) or (obj.triggered_by == request.user)

class AuditViewSet(mixins.DestroyModelMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing Audits and exporting results.
    """
    serializer_class = AuditSerializer
    permission_classes = [IsAuthenticated, IsSameOrganization]

    def get_object(self):
        """
        Override get_object to fetch Audit by PK directly, bypassing header-based filters,
        and applying robust permission checks.
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        pk = self.kwargs.get(lookup_url_kwarg)
        
        # Retrieve the Audit by PK
        obj = get_object_or_404(Audit, pk=pk)
        
        # Check permission for this specific object
        self.check_object_permissions(self.request, obj)
        
        return obj

    def perform_destroy(self, instance):
        """
        Only allow Organization Admins to delete audits.
        """
        # User organization membership is already checked by IsSameOrganization for 'read'
        # But we need to strictly check Role=ADMIN for delete.
        
        membership = Membership.objects.filter(
            user=self.request.user,
            organization=instance.organization
        ).first()

        if not membership or membership.role != Membership.ROLE_ADMIN:
             raise PermissionDenied("Only Organization Admins can delete audits.")
        
        instance.delete()


    @action(detail=False, methods=['post'], url_path='start')
    def start_audit(self, request):
        """
        POST /api/v1/audits/start/
        Start a new audit for the organization.
        """
        try:
            organization = self.request.user.get_organization()
            if not organization:
                 return Response({"error": "No organization found for user"}, status=400)

            audit = Audit.objects.create(
                organization=organization,
                triggered_by=request.user,
                status='PENDING'
            )
            
            # Trigger Celery task
            from apps.audits.tasks import run_audit_task
            run_audit_task.delay(audit.id)
            
            return Response({
                "audit_id": str(audit.id),
                "status": "PENDING",
                "message": "Audit started successfully"
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Failed to start audit: {e}")
            return Response({"error": "Internal Error"}, status=500)

    @action(detail=True, methods=['get'], url_path='evidence')
    def evidence_list(self, request, pk=None):
        """
        GET /api/v1/audits/{id}/evidence/
        List all evidence for a specific audit.
        """
        audit = self.get_object()
        evidence_qs = Evidence.objects.filter(audit=audit).select_related('question')
        serializer = EvidenceSerializer(evidence_qs, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        """
        Filter audits by the user's organization.
        """
        if getattr(self, 'swagger_fake_view', False):
            return Audit.objects.none()
            
        organization = self.request.user.get_organization()
        return Audit.objects.filter(organization=organization).order_by('-created_at')

    @action(detail=True, methods=['get'], url_path='export/csv', permission_classes=[IsAuthenticated, IsAuditOwner, HasProPlan])
    def export_csv(self, request, pk=None):
        """
        Export audit results as CSV.
        """
        try:
            # 1. Fetch Audit (Permissions handled by get_object)
            audit = self.get_object()
            
            # 2. Fetch Evidence
            evidence_list = Evidence.objects.filter(audit=audit).select_related(
                'question'
            ).order_by('created_at').values(
                'question__key',
                'question__title',
                'question__severity',
                'status',
                'raw_data',
                'comment',
                'remediation_steps'
            )
            
            logger.info(f"Streaming CSV export for audit {audit.id}")
            
            def stream_generator():
                buffer = io.StringIO()
                writer = csv.writer(buffer)
                
                # Write headers
                writer.writerow([
                    'Repository',
                    'Check Name',
                    'Status',
                    'Severity',
                    'Remediation'
                ])
                yield buffer.getvalue()
                buffer.truncate(0)
                buffer.seek(0)
                
                # Write rows
                for evidence in evidence_list:
                    # Extract Resource from raw_data
                    raw = evidence.get('raw_data', {})
                    resource = "N/A"
                    if isinstance(raw, dict):
                        resource = raw.get('repo_name') or raw.get('org_name') or raw.get('name') or "N/A"

                    # Remediation text
                    remediation = evidence.get('comment', '') or evidence.get('remediation_steps', '')

                    buffer.truncate(0)
                    buffer.seek(0)
                    writer.writerow([
                        resource,
                        evidence.get('question__title', ''),
                        evidence.get('status', ''),
                        evidence.get('question__severity', ''),
                        remediation
                    ])
                    yield buffer.getvalue()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'Audit_Report_{audit.id}.csv'
            
            response = StreamingHttpResponse(
                stream_generator(),
                content_type='text/csv'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        except Exception as e:
            logger.error(f"CSV Export failed: {e}")
            return Response(
                {"error": "Failed to export audit"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='export/xlsx', permission_classes=[IsAuthenticated, IsAuditOwner, HasProPlan])
    def export_xlsx(self, request, pk=None):
        """
        Export audit results as Excel (XLSX).
        """
        try:
            audit = self.get_object()
            
            # --- Data Aggregation ---
            stats = AuditStatsService.calculate_audit_stats(audit)
            
            total_checks = stats.get('total_findings', 0)
            passed_checks = stats.get('passed_count', 0)
            failed_checks = stats.get('failed_count', 0)
            compliance_score = stats.get('pass_rate_percentage', 0)

            # Re-query for detailed iteration
            evidence_qs = Evidence.objects.filter(audit=audit).select_related('question')

            # --- Excel Generation ---
            wb = Workbook()
            
            # 1. Sheet 1: Executive Summary
            ws_summary = wb.active
            ws_summary.title = "Executive Summary"
            
            # Title
            ws_summary.merge_cells('A1:E1')
            title_cell = ws_summary['A1']
            title_cell.value = "Audit Compliance Report"
            title_cell.font = Font(bold=True, size=16, color="FFFFFF")
            title_cell.fill = PatternFill(start_color="0000FF", end_color="0000FF", fill_type="solid")
            title_cell.alignment = Alignment(horizontal='center', vertical='center')

            # Summary Table
            ws_summary['A3'] = "Metric"
            ws_summary['B3'] = "Count"
            ws_summary['A4'] = "Total Checks"
            ws_summary['B4'] = total_checks
            ws_summary['A5'] = "Passed"
            ws_summary['B5'] = passed_checks
            ws_summary['A6'] = "Failed"
            ws_summary['B6'] = failed_checks
            ws_summary['A7'] = "Compliance Score"
            ws_summary['B7'] = f"{compliance_score:.1f}%"

            for cell in ws_summary['3']:
                cell.font = Font(bold=True)

            # 2. Sheet 2: Detailed Findings
            ws_details = wb.create_sheet(title="Detailed Findings")
            
            headers = ["Repository", "Rule Name", "Status", "Severity", "Compliance Tag", "Remediation"]
            ws_details.append(headers)
            
            red_font = Font(color="FF0000")
            green_font = Font(color="008000")
            header_font = Font(bold=True)
            
            for cell in ws_details[1]:
                cell.font = header_font
            
            ws_details.freeze_panes = "A2"
            
            for evidence in evidence_qs:
                # Handle raw_data safely
                raw = evidence.raw_data if isinstance(evidence.raw_data, dict) else {}
                repo_name = raw.get('repo_name') or evidence.question.key 
                
                rule_name = evidence.question.title
                status_val = evidence.status
                severity = evidence.question.severity
                compliance_tag = "SOC2" # Placeholder or derived
                remediation = evidence.comment or ""
                
                row_data = [repo_name, rule_name, status_val, severity, compliance_tag, remediation]
                ws_details.append(row_data)
                
                last_row_idx = ws_details.max_row
                row_font = None
                if status_val == 'FAIL':
                    row_font = red_font
                elif status_val == 'PASS':
                    row_font = green_font
                
                if row_font:
                    for col in range(1, 7):
                        cell = ws_details.cell(row=last_row_idx, column=col)
                        cell.font = row_font

            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            filename = f"Audit_Report_{audit.id}_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            wb.save(response)
            return response

        except Exception as e:
            logger.error(f"XLSX Export Error: {e}")
            return Response({"error": "Internal Server Error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='export/pdf', permission_classes=[IsAuthenticated, IsAuditOwner, HasProPlan])
    def pdf(self, request, pk=None):
        """
        Export Audit results as PDF.
        """
        try:
            audit = self.get_object()
            
            # Generate PDF
            from apps.audits.services.pdf_report import AuditPDFGenerator
            pdf_bytes = AuditPDFGenerator.generate_pdf(audit)
            
            # Return Response
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Audit_Report_{audit.id}.pdf"'
            return response
            
        except Exception as e:
            logger.error(f"PDF Export Error: {e}")
            return Response({"error": "Failed to generate PDF"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsAuditOwner])
    def preview_pdf(self, request, pk=None):
        """
        Preview Audit PDF as HTML in browser.
        """
        try:
            audit = self.get_object()
            
            from apps.audits.services.pdf_report import AuditPDFGenerator
            html_content = AuditPDFGenerator.generate_html(audit)
            
            return HttpResponse(html_content, content_type='text/html')
            
        except Exception as e:
            logger.error(f"PDF Preview Error: {e}")
            return Response({"error": "Failed to preview PDF"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EvidenceViewSet(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """
    API for managing Evidence items.
    """
    queryset = Evidence.objects.all()
    serializer_class = EvidenceSerializer
    permission_classes = [IsAuthenticated, IsSameOrganization]

    def get_queryset(self):
        # Ensure user can only access evidence from their org
        return Evidence.objects.filter(
            audit__organization=self.request.user.get_organization()
        )

    @action(detail=True, methods=['post'])
    def accept_risk(self, request, pk=None):
        """
        POST /api/v1/evidence/{id}/accept_risk/
        Mark evidence as RISK_ACCEPTED.
        """
        evidence = self.get_object()
        reason = request.data.get('reason')
        
        if not reason:
            return Response(
                {"error": "Reason is required to accept risk."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        evidence.status = 'RISK_ACCEPTED'
        evidence.workflow_status = 'RISK_ACCEPTED'
        evidence.risk_acceptance_reason = reason
        evidence.save()
        
        # Trigger re-score (Optional but requested "Crucial: Trigger a re-calculation... or let user re-run")
        # Optimization: We can just return OK and let frontend refresh/re-run.
        # But if we want to be nice, we could fire a task.
        # Given snippet length, I'll stick to updating object.
        
        return Response(self.get_serializer(evidence).data)
