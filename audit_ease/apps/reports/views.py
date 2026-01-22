from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

# Import your models and the service we just made
from apps.audits.models import Audit
from apps.reports.services import generate_audit_pdf

class AuditReportPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        # 1. Fetch the data
        audit = get_object_or_404(Audit, pk=id)
        findings = audit.findings.all() # Assuming a related name exists

        # 2. Generate the PDF
        try:
            pdf_bytes = generate_audit_pdf(audit, findings)
        except Exception as e:
            # Log the error here
            return HttpResponse("Error generating PDF", status=500)

        # 3. Return the response as a downloadable file
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        
        # 'attachment' forces download. 'inline' would open it in the browser tab.
        filename = f"Audit_Report_{audit.id}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response