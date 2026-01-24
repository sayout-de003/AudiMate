from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

@shared_task
def cleanup_old_reports():
    """
    Deletes PDF files for reports created more than 30 days ago.
    Does NOT delete the Audit record or AuditSnapshot, only the heavy PDF artifact.
    """
    try:
        from apps.reports.models import Report
        
        # Find reports created > 30 days ago
        threshold_date = timezone.now() - timedelta(days=30)
        old_reports = Report.objects.filter(created_at__lte=threshold_date)
        
        count = 0
        for report in old_reports:
            # Delete the file
            if report.file:
                # delete(save=False) removes the file from storage
                # save=False avoids an extra DB save since we delete the model instance immediately after
                report.file.delete(save=False)
                
            # Delete the Report record (which is just a link to the file)
            # The actual Audit data remains in the Audit model
            report.delete()
            count += 1
            
        logger.info(f"Cleanup Task: Deleted {count} old report files.")
        return f"Cleaned up {count} old reports."
        
    except Exception as e:
        logger.exception("Error in cleanup_old_reports task")
        return f"Error: {str(e)}"
