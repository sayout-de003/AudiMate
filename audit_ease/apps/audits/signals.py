from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Audit
from .tasks import send_critical_alert_email_task
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Audit)
def trigger_critical_audit_alert(sender, instance, created, **kwargs):
    """
    Triggered when an Audit is saved.
    Checks if status changed to COMPLETED and if there are critical findings.
    """
    if created:
        return

    # Check if status is COMPLETED
    if instance.status != 'COMPLETED':
        return

    # Optimization: We could check if 'status' is in update_fields if provided, 
    # but strictly checking instance.status == 'COMPLETED' is safer logic-wise 
    # (though might run redundantly if saved multiple times as COMPLETED).
    # Ideally should check if it transitioned, but for now this is safe enough combined with task idempotency check.
    
    # We delay the check for critical issues to the task to keep signal fast,
    # OR we check existence here to avoid queuing useless tasks.
    # User requirement logic: "If Audit.status == 'completed' AND Critical_Count > 0 THEN Send"
    # Let's check count here to prevent spamming Celery with empty tasks.
    
    has_critical_issues = instance.evidence.filter(status='FAIL', question__severity='CRITICAL').exists()
    
    if has_critical_issues:
        logger.info(f"Critical issues detected for Audit {instance.id}. Triggering alert task.")
        # Call the Celery task
        send_critical_alert_email_task.delay(instance.id)
