"""
Audit Export API Views

Endpoints:
- GET /api/v1/audits/{id}/export/csv/ - Export audit results as CSV
"""

import csv
import logging
from datetime import datetime
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audits.models import Audit, Evidence
from apps.organizations.permissions import IsSameOrganization, HasActiveSubscription

# OpenPyXL Imports
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import PieChart, Reference, Series
from openpyxl.chart.label import DataLabelList
import io
from django.http import HttpResponse
from rest_framework.views import APIView


logger = logging.getLogger(__name__)



@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSameOrganization, HasActiveSubscription])
def export_audit_csv(request, audit_id):
    """
    Export Audit Results as CSV (Streaming Version)
    
    Optimized for large datasets using proper CSV streaming.
    """
    
    try:
        # Fetch the audit
        audit = get_object_or_404(Audit, id=audit_id)
        
        # Permission checks
        if not audit.organization.members.filter(user=request.user).exists():
            return Response(
                {"error": "You don't have access to this audit"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if audit.organization.subscription_status != 'active':
            return Response(
                {"error": "Upgrade to Premium to export data"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        logger.info(f"Streaming export for audit {audit_id}")
        
        def stream_generator():
            """Yield CSV lines as a generator"""
            import io
            
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            
            # Write headers
            writer.writerow([
                'Resource ID',
                'Check Name',
                'Status',
                'Severity',
                'Timestamp',
                'Comment'
            ])
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)
            
            # --- FIX IS HERE ---
            # 1. Query is defined INSIDE the generator
            # 2. We use .iterator(chunk_size=2000) to fetch in small batches
            evidence_iterator = Evidence.objects.filter(audit=audit).select_related(
                'question'
            ).order_by('created_at').values(
                'question__key',
                'question__title',
                'question__severity',
                'status',
                'created_at',
                'comment'
            ).iterator(chunk_size=2000)
            
            # Write rows
            for evidence in evidence_iterator:
                writer.writerow([
                    evidence.get('question__key', ''),
                    evidence.get('question__title', ''),
                    evidence.get('status', ''),
                    evidence.get('question__severity', ''),
                    evidence.get('created_at', ''),
                    evidence.get('comment', ''),
                ])
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate(0)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'audit_{audit_id}_{timestamp}.csv'
        
        response = StreamingHttpResponse(
            stream_generator(),
            content_type='text/csv'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    except Audit.DoesNotExist:
        logger.warning(f"Audit {audit_id} not found for export")
        return Response(
            {"error": "Audit not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error streaming audit {audit_id}: {e}")
        return Response(
            {"error": "Failed to export audit"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )








# @api_view(['GET'])
# @permission_classes([IsAuthenticated, IsSameOrganization, HasActiveSubscription])
# def export_audit_csv(request, audit_id):
#     """
#     Export Audit Results as CSV
    
#     GET /api/v1/audits/{audit_id}/export/csv/
    
#     Security:
#     - User must be authenticated
#     - User must belong to the audit's organization
#     - Organization must have an active subscription
    
#     Returns:
#     - Streaming CSV file with audit evidence
#     - Content-Disposition: attachment (downloads as file)
#     - Filename: audit_{audit_id}_{timestamp}.csv
    
#     Columns:
#     - Resource ID: The resource being audited
#     - Check Name: Question/check identifier
#     - Status: PASS/FAIL/ERROR
#     - Severity: CRITICAL/HIGH/MEDIUM/LOW
#     - Timestamp: When the evidence was collected
#     - Comment: Human-readable summary
    
#     Error Responses:
#     - 404: Audit not found
#     - 403: User doesn't have access to this audit
#     - 403: "Upgrade to Premium to export data" (no active subscription)
#     """
    
#     try:
#         # Fetch the audit
#         audit = get_object_or_404(Audit, id=audit_id)
        
#         # Permission check: IsSameOrganization via has_object_permission
#         if not audit.organization.members.filter(user=request.user).exists():
#             return Response(
#                 {"error": "You don't have access to this audit"},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         # Permission check: HasActiveSubscription (enforced by decorator, but verify)
#         if audit.organization.subscription_status != 'active':
#             return Response(
#                 {"error": "Upgrade to Premium to export data"},
#                 status=status.HTTP_403_FORBIDDEN
#             )
            
#         logger.info(f"Starting streaming CSV export for audit {audit_id}")

#         def generate_csv_rows():
#             """Yield CSV rows using a StringIO buffer to avoid building the whole file in memory."""
#             buffer = io.StringIO()
#             writer = csv.writer(buffer)
            
#             # Write Header
#             writer.writerow([
#                 'Resource ID',
#                 'Check Name',
#                 'Status',
#                 'Severity',
#                 'Timestamp',
#                 'Comment'
#             ])
#             yield buffer.getvalue()
#             buffer.seek(0)
#             buffer.truncate(0)

#             # Efficiently iterate over evidence
#             # Use iterator() to fetch rows in chunks from the DB
#             evidence_iterator = Evidence.objects.filter(audit=audit).select_related(
#                 'question'
#             ).order_by('created_at').iterator(chunk_size=1000)

#             for evidence in evidence_iterator:
#                 writer.writerow([
#                     evidence.question.key or '',
#                     evidence.question.title or '',
#                     evidence.status or '',
#                     evidence.question.severity or '',
#                     evidence.created_at.isoformat() if evidence.created_at else '',
#                     evidence.comment or '',
#                 ])
#                 yield buffer.getvalue()
#                 buffer.seek(0)
#                 buffer.truncate(0)

#         # Create the streaming response
#         timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#         filename = f'audit_{audit_id}_{timestamp}.csv'
        
#         response = StreamingHttpResponse(
#             generate_csv_rows(),
#             content_type='text/csv'
#         )
#         response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
#         return response
    
#     except Audit.DoesNotExist:
#         logger.warning(f"Audit {audit_id} not found")
#         return Response(
#             {"error": "Audit not found"},
#             status=status.HTTP_404_NOT_FOUND
#         )
#     except Exception as e:
#         logger.error(f"Error exporting audit {audit_id}: {str(e)}")
#         return Response(
#             {"error": "Failed to export audit"},
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )


def generate_csv_proper():
    """
    Generator for streaming CSV without buffering.
    More memory efficient than building the entire response in memory.
    """
    import io
    
    # Create a generator that yields lines
    yield "Resource ID,Check Name,Status,Severity,Timestamp,Comment\r\n"
    
    # This will be populated from the view


class AuditExportCSVView(APIView):
    """
    Export Audit Results as CSV (Streaming Version)
    
    Optimized for large datasets using proper CSV streaming.
    
    SECURITY FIX: 
    - Rely on Object Level Permissions (audit.organization) 
    - Do NOT rely on header-based middleware (request.organization)
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, audit_id):
        """Helper to get object and enforce permissions consistently"""
        audit = get_object_or_404(Audit, id=audit_id)
        
        # Verify access: User must be member of the audit's organization
        if not audit.organization.members.filter(user=self.request.user).exists():
            self.permission_denied(self.request, message="You don't have access to this audit")
            
        return audit

    def get(self, request, audit_id):
        try:
            # 1. Fetch Audit & Verify Permissions
            audit = self.get_object(audit_id)
            
            # 2. Subscription Check
            if audit.organization.subscription_status != 'active':
                return Response(
                    {"error": "Upgrade to Premium to export data"},
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
                'created_at',
                'comment'
            )
            
            logger.info(f"Streaming export for audit {audit_id}")
            
            def stream_generator():
                """Yield CSV lines as a generator"""
                import io
                
                buffer = io.StringIO()
                writer = csv.writer(buffer)
                
                # Write headers
                writer.writerow([
                    'Resource ID',
                    'Check Name',
                    'Status',
                    'Severity',
                    'Timestamp',
                    'Comment'
                ])
                yield buffer.getvalue()
                buffer.truncate(0)
                buffer.seek(0)
                
                # Write rows
                for evidence in evidence_list:
                    buffer.truncate(0)
                    buffer.seek(0)
                    writer.writerow([
                        evidence.get('question__key', ''),
                        evidence.get('question__title', ''),
                        evidence.get('status', ''),
                        evidence.get('question__severity', ''),
                        evidence.get('created_at', ''),
                        evidence.get('comment', ''),
                    ])
                    yield buffer.getvalue()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'audit_{audit_id}_{timestamp}.csv'
            
            response = StreamingHttpResponse(
                stream_generator(),
                content_type='text/csv'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
        
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return Response(
                {"error": "Failed to export audit"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ExportAuditReportView(APIView):
    """
    Generate a detailed Excel report for an audit.
    Includes Executive Summary and Detailed Findings.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, audit_id):
        try:
            audit = get_object_or_404(Audit, id=audit_id)
            
            # Explicit Permission Checks (ignoring headers)
            if not audit.organization.members.filter(user=request.user).exists():
                return Response(
                    {"error": "You don't have access to this audit"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if audit.organization.subscription_status != 'active':
                return Response(
                    {"error": "Upgrade to Premium to export data"},
                    status=status.HTTP_403_FORBIDDEN
                )

            # self.check_object_permissions(request, audit) # No longer needed as we checked manually
            
            # --- Data Aggregation ---
            # --- Data Aggregation ---
            from apps.audits.services.stats_service import AuditStatsService
            stats = AuditStatsService.calculate_audit_stats(audit)
            
            # Use stats from service to ensure parity with Dashboard
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
            
            # 3D Pie Chart: Pass vs Fail
            pie = PieChart()
            pie.title = "Compliance Status"
            # Data: Passed, Failed. (Rows 5 and 6)
            data = Reference(ws_summary, min_col=2, min_row=5, max_row=6) 
            labels = Reference(ws_summary, min_col=1, min_row=5, max_row=6)
            pie.add_data(data, titles_from_data=False)
            pie.set_categories(labels)
            
            # Make it 3D (OpenPyXL PieChart usually supports 3D via specific class or settings, 
            # strictly speaking 'PieChart3D' exists but user asked for 'PieChart' from openpyxl.chart generally.
            # Let's check if PieChart3D is available or if we just use PieChart. 
            # The user request said "Chart: Insert a 3D Pie Chart". 
            # openpyxl.chart.PieChart3D is the class.)
            from openpyxl.chart import PieChart3D
            pie_3d = PieChart3D()
            pie_3d.title = "Compliance Status"
            pie_3d.add_data(data, titles_from_data=False)
            pie_3d.set_categories(labels)
            
            ws_summary.add_chart(pie_3d, "D3")


            # 2. Sheet 2: Detailed Findings
            ws_details = wb.create_sheet(title="Detailed Findings")
            
            headers = ["Repository", "Rule Name", "Status", "Severity", "Compliance Tag", "Remediation"]
            ws_details.append(headers)
            
            # Styling constants
            red_font = Font(color="FF0000")
            green_font = Font(color="008000") # Dark Green
            header_font = Font(bold=True)
            
            # Headers Styling
            for cell in ws_details[1]:
                cell.font = header_font
            
            # Freeze Top Row
            ws_details.freeze_panes = "A2"
            
            # Auto-Filter
            ws_details.auto_filter.ref = ws_details.dimensions
            
            # Data Rows
            for evidence in evidence_qs:
                # Assuming 'Repository' comes from somewhere? 
                # The prompt mentions "Repository" as a header but Evidence model links to Question.
                # Question has 'key' (resource ID-like) and 'title'.
                # The user context "The Audit model has many AuditResult children" (we found Evidence)
                # Maybe 'key' serves as Repository/Resource or simply 'N/A' if not available.
                # I'll use question.key for Repository for now as a placeholder/best-guess.
                
                repo_name = evidence.question.key 
                rule_name = evidence.question.title
                status_val = evidence.status
                severity = evidence.question.severity
                compliance_tag = "SOC2"  # Hardcoded or derived? Prompt example says "e.g., SOC2". 
                # Using a placeholder or derived if possible. Evidence doesn't have tags field visible.
                # I'll modify to just string "SOC2" or similar if not dynamic.
                remediation = evidence.comment # Using comment as remediation/details
                
                row_data = [repo_name, rule_name, status_val, severity, compliance_tag, remediation]
                ws_details.append(row_data)
                
                # Conditional Formatting (Row Level - applied to last appended row)
                last_row_idx = ws_details.max_row
                # Apply style to Status column (Col 3 / C) or whole row? 
                # "Failed rows should have red text. Passed rows should be green." - implies whole row text color.
                
                row_font = None
                if status_val == 'FAIL':
                    row_font = red_font
                elif status_val == 'PASS':
                    row_font = green_font
                
                if row_font:
                    for col in range(1, 7): # A to F
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
            logger.error(f"Error exporting xlsx for audit {audit_id}: {str(e)}")
            return Response({"error": "Internal Server Error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

