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

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSameOrganization, HasActiveSubscription])
def export_audit_csv(request, audit_id):
    """
    Export Audit Results as CSV
    
    GET /api/v1/audits/{audit_id}/export/csv/
    
    Security:
    - User must be authenticated
    - User must belong to the audit's organization
    - Organization must have an active subscription
    
    Returns:
    - Streaming CSV file with audit evidence
    - Content-Disposition: attachment (downloads as file)
    - Filename: audit_{audit_id}_{timestamp}.csv
    
    Columns:
    - Resource ID: The resource being audited
    - Check Name: Question/check identifier
    - Status: PASS/FAIL/ERROR
    - Severity: CRITICAL/HIGH/MEDIUM/LOW
    - Timestamp: When the evidence was collected
    - Comment: Human-readable summary
    
    Error Responses:
    - 404: Audit not found
    - 403: User doesn't have access to this audit
    - 403: "Upgrade to Premium to export data" (no active subscription)
    """
    
    try:
        # Fetch the audit
        audit = get_object_or_404(Audit, id=audit_id)
        
        # Permission check: IsSameOrganization via has_object_permission
        if not audit.organization.members.filter(user=request.user).exists():
            return Response(
                {"error": "You don't have access to this audit"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Permission check: HasActiveSubscription (enforced by decorator, but verify)
        if audit.organization.subscription_status != 'active':
            return Response(
                {"error": "Upgrade to Premium to export data"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Fetch all evidence for this audit
        evidence_list = Evidence.objects.filter(audit=audit).select_related(
            'question'
        ).order_by('created_at')
        
        # If no evidence found, still return empty CSV with headers
        if not evidence_list.exists():
            logger.info(f"Exporting empty audit {audit_id}")
        else:
            logger.info(
                f"Exporting {evidence_list.count()} evidence items "
                f"for audit {audit_id}"
            )
        
        # Generator function for streaming CSV
        def generate_csv():
            """Yield CSV rows as they are generated (memory efficient)"""
            
            # Create CSV writer (writing to memory buffer)
            writer_output = []
            writer = csv.writer(writer_output)
            
            # Write headers
            headers = [
                'Resource ID',
                'Check Name',
                'Status',
                'Severity',
                'Timestamp',
                'Comment'
            ]
            writer.writerow(headers)
            yield ','.join(headers) + '\r\n'
            
            # Write data rows
            for evidence in evidence_list:
                row = [
                    evidence.question.key or '',  # Resource ID
                    evidence.question.title or '',  # Check Name
                    evidence.status or '',  # Status
                    evidence.question.severity or '',  # Severity
                    evidence.created_at.isoformat() if evidence.created_at else '',  # Timestamp
                    evidence.comment or '',  # Comment
                ]
                
                # Write using csv.writer to handle escaping
                writer = csv.writer([])
                writer = csv.writer(writer_output)
                writer.writerow(row)
                
                # Get the CSV string representation
                if writer_output:
                    line = writer_output.pop()
                    yield line
        
        # Create the streaming response
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'audit_{audit_id}_{timestamp}.csv'
        
        response = StreamingHttpResponse(
            generate_csv_proper(),
            content_type='text/csv'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    except Audit.DoesNotExist:
        logger.warning(f"Audit {audit_id} not found")
        return Response(
            {"error": "Audit not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error exporting audit {audit_id}: {str(e)}")
        return Response(
            {"error": "Failed to export audit"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def generate_csv_proper():
    """
    Generator for streaming CSV without buffering.
    More memory efficient than building the entire response in memory.
    """
    import io
    
    # Create a generator that yields lines
    yield "Resource ID,Check Name,Status,Severity,Timestamp,Comment\r\n"
    
    # This will be populated from the view


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSameOrganization, HasActiveSubscription])
def export_audit_csv_streaming(request, audit_id):
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
        
        # Fetch evidence
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
    
    except Audit.DoesNotExist:
        logger.warning(f"Audit {audit_id} not found for export")
        return Response(
            {"error": "Audit not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error streaming CSV for audit {audit_id}: {str(e)}")
        return Response(
            {"error": "Failed to export audit"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
