from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

# Import your models and the service we just made
from apps.audits.models import Audit
from apps.reports.services import generate_audit_pdf

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
        
        # Check if report already exists
        if hasattr(audit, 'report'):
             # Return existing file
             response = HttpResponse(audit.report.file.read(), content_type='application/pdf')
             filename = f"Audit_Report_{audit.id}.pdf"
             response['Content-Disposition'] = f'attachment; filename="{filename}"'
             return response

        findings = audit.evidence.all() # Correct related_name is 'evidence'

        # 2. Generate the PDF
        try:
            pdf_bytes = generate_audit_pdf(audit, findings)
            
            # Save the report for cost-saving cleanup later
            from django.core.files.base import ContentFile
            from apps.reports.models import Report
            
            report = Report(audit=audit)
            # ContentFile needs a name, but FieldFile.save takes a name
            report.file.save(f"Audit_Report_{audit.id}.pdf", ContentFile(pdf_bytes))
            # report.save() is called automatically by file.save()
            
        except Exception as e:
            # Log the error here
            return HttpResponse("Error generating PDF", status=500)

        # 3. Return the response as a downloadable file
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        
        # 'attachment' forces download. 'inline' would open it in the browser tab.
        filename = f"Audit_Report_{audit.id}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response