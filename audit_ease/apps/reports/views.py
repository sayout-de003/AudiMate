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

        # Check if report already exists and we are not forcing or in html mode
        if hasattr(audit, 'report') and not force and not html_mode:
             # Return existing file (simple serving)
             try:
                 response = HttpResponse(audit.report.file.read(), content_type='application/pdf')
                 filename = f"Audit_Report_{audit.id}.pdf"
                 response['Content-Disposition'] = f'attachment; filename="{filename}"'
                 return response
             except Exception:
                 # If file is missing, fall through to regenerate
                 pass

        # --- DATA PREPARATION (Match logic from AuditViewSet) ---
        
        # 1. Scoring
        score = calculate_audit_score(audit)
        audit.score_value = score
        audit.save(update_fields=['score_value'])

        # 2. Stats
        evidence_qs = Evidence.objects.filter(audit=audit).select_related('question')
        
        passed_checks = evidence_qs.filter(status='PASS').count()
        failed_checks = evidence_qs.filter(status='FAIL').count()
        critical_fails = evidence_qs.filter(status='FAIL', question__severity='CRITICAL').count()
        high_fails = evidence_qs.filter(status='FAIL', question__severity='HIGH').count()
        
        stats = {
            'passing': passed_checks,
            'critical': critical_fails,
            'high': high_fails,
            'failed': failed_checks,
            'total': evidence_qs.count()
        }

        # 3. Construct "Checks" List & Sorting
        severity_map = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        
        checks = []
        for ev in evidence_qs:
            checks.append({
                'rule_id': ev.question.key,
                'title': ev.question.title,
                'description': ev.question.description,
                'severity': ev.question.severity,
                'status': ev.status,
                'evidence': ev,
            })
            
        def sort_key(c):
             # Failures first, then by severity
            status_order = 1 if c['status'] == 'PASS' else 0
            sev_index = severity_map.get(c['severity'], 4)
            return (status_order, sev_index)

        checks_sorted = sorted(checks, key=sort_key)

        # 4. Pie Chart
        pie_chart_base64 = None
        if passed_checks + failed_checks > 0:
            plt.figure(figsize=(6, 6))
            labels = ['Pass', 'Fail']
            sizes = [passed_checks, failed_checks]
            colors = ['#2e7d32', '#c62828'] 
            plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            plt.axis('equal')
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight')
            buffer.seek(0)
            pie_chart_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            plt.close()

        # 5. Render
        context = {
            'audit': audit,
            'score': score,
            'stats': stats,
            'checks': checks_sorted,
            'pie_chart': pie_chart_base64,
        }
        
        html_string = render_to_string('reports/audit_report.html', context)

        if html_mode:
            return HttpResponse(html_string, content_type='text/html')

        # 6. Generate PDF
        try:
            # We use WeasyPrint directly here instead of the service to ensure context is right
            # base_url is needed for images
            pdf_file = io.BytesIO()
            HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(target=pdf_file)
            pdf_bytes = pdf_file.getvalue()
            
            # Save the report model if needed... (Skipping strictly for response speed, or could save here)
            # Keeping it simple: return the PDF
            
        except Exception as e:
            return HttpResponse(f"Error generating PDF: {str(e)}", status=500)

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"Audit_Report_{audit.id}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response