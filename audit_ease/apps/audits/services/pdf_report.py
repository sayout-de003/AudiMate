
import io
import base64
from reportlab.graphics.shapes import Drawing
from django.template.loader import render_to_string
from weasyprint import HTML, CSS
import matplotlib.pyplot as plt
from django.db import models

class AuditPDFGenerator:
    """
    Generates a professional PDF report for an Audit.
    """
    
    @staticmethod
    def generate_pdf(audit):
        """
        Generates PDF bytes for the given audit.
        """
        # 1. Prepare Data
        html_string = AuditPDFGenerator.generate_html(audit)
        
        # 2. Convert to PDF
        pdf_file = HTML(string=html_string, base_url="").write_pdf()
        
        return pdf_file

    @staticmethod
    def generate_html(audit):
        """
        Generates the HTML string for the report (useful for previews).
        """
        from apps.audits.models import Evidence
        
        # Stats
        total_ev = Evidence.objects.filter(audit=audit).count()
        passed_ev = Evidence.objects.filter(audit=audit, status='PASS').count()
        failed_ev = Evidence.objects.filter(audit=audit, status='FAIL').exclude(workflow_status='RISK_ACCEPTED').count()
        risk_accepted = Evidence.objects.filter(audit=audit).filter(
            models.Q(status='RISK_ACCEPTED') | models.Q(workflow_status='RISK_ACCEPTED')
        ).count()
        
        stats = {
            'total': total_ev,
            'passed': passed_ev,
            'failed': failed_ev,
            'risk_accepted': risk_accepted
        }
        
        # Failures (Visuals)
        # Filter failures for the report tables (Excluding risk accepted)
        critical_high = Evidence.objects.filter(
            audit=audit, 
            status='FAIL', 
            question__severity__in=['CRITICAL', 'HIGH']
        ).exclude(
            workflow_status='RISK_ACCEPTED'
        ).select_related('question')
        
        other_findings = Evidence.objects.filter(
            audit=audit
        ).exclude(
            id__in=critical_high.values('id')
        ).select_related('question')
        
        # Chart
        chart_base64 = AuditPDFGenerator._generate_pie_chart(passed_ev, failed_ev)
        
        context = {
            'audit': audit,
            'stats': stats,
            'critical_high_findings': critical_high,
            'other_findings': other_findings,
            'failures': Evidence.objects.filter(audit=audit, status='FAIL'), # for count in template
            'chart_image': chart_base64
        }
        
        return render_to_string('reports/audit_report.html', context)

    @staticmethod
    def _generate_pie_chart(passed, failed):
        """
        Generates a Pie Chart as a base64 string.
        """
        if passed == 0 and failed == 0:
            return None
            
        labels = ['Passed', 'Failed']
        sizes = [passed, failed]
        colors = ['#4CAF50', '#F44336'] # Green, Red
        explode = (0.1, 0)  # explode 1st slice

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
               shadow=True, startangle=140)
        ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        plt.close(fig) # Close to free memory
        
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        
        graphic = base64.b64encode(image_png)
        return graphic.decode('utf-8')
