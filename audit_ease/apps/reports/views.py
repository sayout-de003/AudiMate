from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

# Import your models and the service we just made
from apps.audits.models import Audit, Evidence
from apps.reports.services import generate_audit_pdf
from apps.audits.services.stats_service import AuditStatsService
from utils.scoring import calculate_audit_score
from django.template.loader import render_to_string
from weasyprint import HTML
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64

from rest_framework.throttling import ScopedRateThrottle
from apps.core.permissions import HasPremiumFeatureAccess

class AuditReportPDFView(APIView):
    permission_classes = [IsAuthenticated, HasPremiumFeatureAccess]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'pdf_generation'

    def get(self, request, id):
        # 1. Fetch the data
        # Critical: Ensure tenant isolation. 
        # User can only access audits belonging to their organization.
        audit = get_object_or_404(Audit, pk=id, organization=request.user.get_organization())
        
        # Check if force regeneration is requested
        force = request.query_params.get('force', 'false').lower() == 'true'
        html_mode = request.query_params.get('format', '').lower() == 'html'

        # --- DATA PREPARATION (Match logic from AuditExportPDFView) ---
        
        # 1. Stats
        from apps.audits.services.stats_service import AuditStatsService
        stats = AuditStatsService.calculate_audit_stats(audit)

        # 2. Fetch all evidence
        evidence_qs = Evidence.objects.filter(audit=audit).select_related('question').order_by('question__severity', 'question__key')

        # 3. Grouping Logic
        import json
        from datetime import datetime
        
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
                    'passed_count': 0
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

            if ev.status == 'PASS':
                check['passed_count'] += 1

        # 4. Convert to list & Sort
        checks_list = list(grouped_checks.values())
        severity_map = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        checks_list.sort(key=lambda x: (
            0 if x['status'] == 'FAIL' else 1,
            severity_map.get(x['severity'], 4)
        ))

        # 5. Render
        context = {
            'audit': audit,
            'stats': stats,
            'checks': checks_list,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        }
        
        # USE THE FIXED TEMPLATE
        html_string = render_to_string('reports/audit_report_fixed.html', context)

        if html_mode:
            return HttpResponse(html_string, content_type='text/html')

        # 6. Generate PDF
        try:
            # We use WeasyPrint directly here instead of the service to ensure context is right
            # base_url is needed for images
            pdf_file = io.BytesIO()
            HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(target=pdf_file)
            pdf_bytes = pdf_file.getvalue()
            
        except Exception as e:
            return HttpResponse(f"Error generating PDF: {str(e)}", status=500)

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"Audit_Report_{audit.id}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response