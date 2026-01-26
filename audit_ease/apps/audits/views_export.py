"""
Audit Export API Views

Endpoints:
- GET /api/v1/audits/{id}/export/csv/ - Export audit results as CSV
- GET /api/v1/audits/{id}/export/xlsx/ - Export audit results as Excel
- GET /api/v1/audits/{id}/export/pdf/ - Export audit results as PDF
"""

import csv
import logging
import io
from datetime import datetime
from django.http import StreamingHttpResponse, HttpResponse, FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audits.models import Audit, Evidence
from apps.organizations.permissions import IsSameOrganization, HasActiveSubscription

# WeasyPrint Imports
try:
    import weasyprint
except ImportError:
    pass

import json
from django.template.loader import render_to_string
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import PieChart, PieChart3D, Reference


logger = logging.getLogger(__name__)


class AuditExportCSVView(APIView):
    """
    Export Audit Results as CSV (Streaming Version)
    
    Optimized for large datasets using proper CSV streaming.
    """
    permission_classes = [IsAuthenticated, IsSameOrganization]

    def get(self, request, audit_id):
        try:
            # 1. Fetch Audit & Verify Permissions
            audit = get_object_or_404(Audit, id=audit_id)
            self.check_object_permissions(request, audit)
            
            # 2. Subscription Check
            if audit.organization.subscription_status != 'active':
                return Response(
                    {"error": "Subscribe to download"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # 3. Fetch Evidence
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
            
            logger.info(f"Streaming CSV export for audit {audit_id}")
            
            def stream_generator():
                """Yield CSV lines as a generator"""
                import io
                
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
            filename = f'Audit_Report_{audit_id}.csv'
            
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


class AuditExportPDFView(APIView):
    """
    Export Audit Results as PDF using WeasyPrint.
    Industry-standard design with deduplicated findings.
    """
    permission_classes = [IsAuthenticated, IsSameOrganization]

    def _get_report_context(self, audit):
        """
        Shared context generation for PDF and HTML Preview.
        """
        # Prepare stats
        from apps.audits.services.stats_service import AuditStatsService
        stats = AuditStatsService.calculate_audit_stats(audit)

        # Fetch all evidence
        evidence_qs = Evidence.objects.filter(audit=audit).select_related('question').order_by('question__severity', 'question__key')

        # Grouping Logic
        grouped_checks = {}
        for ev in evidence_qs:
            rule_key = ev.question.key
            if rule_key not in grouped_checks:
                grouped_checks[rule_key] = {
                    'rule_id': ev.question.key, 
                    'title': ev.question.title,
                    'description': ev.question.description,
                    'severity': ev.question.severity,
                    'status': 'PASS', # Assume pass until failure found
                    'findings': [],
                    'passed_count': 0  # Track passed resources count
                }
            
            check = grouped_checks[rule_key]
            
            # Check status aggregation
            if ev.status == 'FAIL':
                check['status'] = 'FAIL'
            elif ev.status == 'ERROR' and check['status'] != 'FAIL':
                check['status'] = 'ERROR'
            
            # Extract resource name
            raw = ev.raw_data
            resource = "N/A"
            if isinstance(raw, dict):
                resource = raw.get('repo_name') or raw.get('org_name') or raw.get('name') or "N/A"
            
            # Serialize JSON for display
            json_log = json.dumps(raw, indent=2, default=str) if raw else None
            
            check['findings'].append({
                'resource': resource,
                'status': ev.status,
                'screenshot': ev.screenshot,
                'raw_data': raw,
                'json_log': json_log,
                'comment': ev.comment,
                'remediation': ev.remediation_steps
            })

            # Count passed resources
            # In a real scenario, we might want to know how many were scanned effectively.
            # If the check is PASS, usually it means all scanned resources passed. 
            # If we have granular findings for each passed resource, we count them.
            # Otherwise, we might default to 1 if it's a singleton check.
            # Here we just count the evidence items.
            if ev.status == 'PASS':
                check['passed_count'] += 1

        # Convert to list
        checks_list = list(grouped_checks.values())
        
        # Sort: FAIL first, then by Severity
        severity_map = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        checks_list.sort(key=lambda x: (
            0 if x['status'] == 'FAIL' else 1,
            severity_map.get(x['severity'], 4)
        ))

        return {
            'audit': audit,
            'stats': stats,
            'checks': checks_list,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        }

    def get(self, request, audit_id):
        try:
            # Optimize query to include organization for template rendering
            audit = get_object_or_404(Audit.objects.select_related('organization'), id=audit_id)
            self.check_object_permissions(request, audit)

            if audit.organization.subscription_status != 'active':
                return Response(
                    {"error": "Subscribe to download"},
                    status=status.HTTP_403_FORBIDDEN
                )

            context = self._get_report_context(audit)

            # Generate PDF
            html_string = render_to_string('reports/audit_report_fixed.html', context)
            
            # Use base_url for loading static files/images locally if needed
            # For file:// paths in src, WeasyPrint usually handles them if absolute.
            pdf_file = weasyprint.HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()

            response = HttpResponse(pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Audit_Report_{audit_id}.pdf"'
            return response

        except Exception as e:
            logger.exception(f"PDF Export Error: {e}")
            return Response({"error": "Failed to generate PDF"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AuditExportPreviewView(AuditExportPDFView):
    """
    Render Audit Report as HTML for preview.
    """
    def get(self, request, audit_id):
        try:
            audit = get_object_or_404(Audit.objects.select_related('organization'), id=audit_id)
            self.check_object_permissions(request, audit)

            # NOTE: We allow preview even if not subscribed? 
            # Spec doesn't say, but usually preview is fine or same restriction.
            # Let's keep consistency with PDF view for now.
            if audit.organization.subscription_status != 'active':
                 return Response(
                    {"error": "Subscribe to view report"},
                    status=status.HTTP_403_FORBIDDEN
                )

            context = self._get_report_context(audit)
            content = render_to_string('reports/audit_report_fixed.html', context)
            return HttpResponse(content)
            
        except Exception as e:
            logger.exception(f"Report Preview Error: {e}")
            return Response({"error": "Failed to generate preview"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExportAuditReportView(APIView):
    """
    Generate a detailed Excel report for an audit.
    Includes Executive Summary and Detailed Findings.
    """
    permission_classes = [IsAuthenticated, IsSameOrganization]

    def get(self, request, audit_id):
        try:
            audit = get_object_or_404(Audit, id=audit_id)
            self.check_object_permissions(request, audit)
            
            if audit.organization.subscription_status != 'active':
                return Response(
                    {"error": "Subscribe to download"},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Dependency Check
            from apps.audits.services.stats_service import AuditStatsService

            # --- Data Aggregation ---
            stats = AuditStatsService.calculate_audit_stats(audit)
            
            total_checks = stats['total_findings']
            passed_checks = stats['passed_count']
            failed_checks = stats['failed_count']
            compliance_score = stats['pass_rate_percentage']

            # Re-query for detailed iteration (Sheet 2)
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
            title_cell.fill = PatternFill(start_color="0000FF", end_color="0000FF", fill_type="solid") # Blue Background
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

            # Style Table Headers
            for cell in ws_summary['3']:
                cell.font = Font(bold=True)
            
            # Chart: Compliance Status
            pie = PieChart()
            pie.title = "Compliance Status"
            data = Reference(ws_summary, min_col=2, min_row=5, max_row=6) 
            labels = Reference(ws_summary, min_col=1, min_row=5, max_row=6)
            pie.add_data(data, titles_from_data=False)
            pie.set_categories(labels)
            
            # Try 3D if imported
            try:
                from openpyxl.chart import PieChart3D
                pie_3d = PieChart3D()
                pie_3d.title = "Compliance Status"
                pie_3d.add_data(data, titles_from_data=False)
                pie_3d.set_categories(labels)
                ws_summary.add_chart(pie_3d, "D3")
            except:
                ws_summary.add_chart(pie, "D3")


            # 2. Sheet 2: Detailed Findings
            ws_details = wb.create_sheet(title="Detailed Findings")
            
            headers = ["Repository", "Rule Name", "Status", "Severity", "Compliance Tag", "Remediation"]
            ws_details.append(headers)
            
            # Styling constants
            red_font = Font(color="FF0000")
            green_font = Font(color="008000")
            header_font = Font(bold=True)
            
            # Headers Styling
            for cell in ws_details[1]:
                cell.font = header_font
            
            # Freeze Top Row
            ws_details.freeze_panes = "A2"
            
            # Data Rows
            for evidence in evidence_qs:
                repo_name = evidence.question.key 
                rule_name = evidence.question.title
                status_val = evidence.status
                severity = evidence.question.severity
                compliance_tag = "SOC2"
                remediation = evidence.comment
                
                row_data = [repo_name, rule_name, status_val, severity, compliance_tag, remediation]
                ws_details.append(row_data)
                
                # Conditional Formatting
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

            # --- Final Response ---
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            filename = f"Audit_Report_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            wb.save(response)
            return response

        except Audit.DoesNotExist:
             return Response({"error": "Audit not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"XLSX Export Error: {e}")
            return Response({"error": "Internal Server Error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
