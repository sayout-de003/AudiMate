from django.template.loader import render_to_string
from weasyprint import HTML
from django.utils import timezone
import io

def generate_audit_pdf(audit_instance, findings_list):
    """
    Generates a PDF for a specific audit.
    
    Args:
        audit_instance: The Audit model object.
        findings_list: A QuerySet or list of Finding objects.
        
    Returns:
        bytes: The PDF binary data.
    """
    
    # 1. Render the HTML with context data
    context = {
        'audit': audit_instance,
        'findings': findings_list,
        'report_date': timezone.now(),
    }
    
    html_string = render_to_string('reports/audit_report.html', context)
    
    # 2. Convert HTML to PDF using WeasyPrint
    # We write to a BytesIO buffer to keep it in memory (fast) rather than disk
    pdf_file = io.BytesIO()
    
    HTML(string=html_string).write_pdf(target=pdf_file)
    
    # 3. Reset the file pointer to the beginning so it can be read
    pdf_file.seek(0)
    
    return pdf_file.getvalue()