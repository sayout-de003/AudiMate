from celery import shared_task
from .models import Audit
from .logic import AuditExecutor
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def run_audit_task(self, audit_id):
    """
    Executes the audit logic asynchronously.
    Runs all configured compliance checks against the organization's integrations.
    """
    try:
        audit = Audit.objects.get(id=audit_id)
        
        # Execute real audit checks via AuditExecutor
        executor = AuditExecutor(audit.id)
        checks_executed = executor.execute_checks()
        
        logger.info(f"Audit {audit.id} completed with {checks_executed} checks")
        return {'status': 'Audit Completed', 'audit_id': str(audit.id), 'checks_executed': checks_executed}

    except Exception as e:
        logger.exception(f"Audit task failed for {audit_id}: {e}")
        try:
            audit = Audit.objects.get(id=audit_id)
            audit.status = 'FAILED'
            audit.save()
        except:
            pass
        # Re-raise so Celery knows the task failed
        raise e

@shared_task
def generate_pdf_task(audit_id):
    """
    Generates the PDF for a completed audit.
    Placeholder for Phase 4 implementation.
    """
    try:
        audit = Audit.objects.get(id=audit_id)
        logger.info(f"PDF generation queued for audit {audit_id}")
        
        # TODO: Implement PDF generation in Phase 4
        # pdf_service = PDFGeneratorService(audit)
        # pdf_path = pdf_service.generate()
        
        return {'status': 'PDF generation queued', 'audit_id': str(audit_id)}
        
    except Exception as e:
        logger.exception(f"PDF generation task failed for {audit_id}: {e}")
        raise e