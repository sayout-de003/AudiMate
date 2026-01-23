from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from apps.audits.models import Audit  # Import your Audit model

@receiver(post_save, sender=Audit)
def send_audit_completion_email(sender, instance, created, **kwargs):
    # Check if the audit is marked as completed
    # Only send email when status changes to COMPLETED and not on creation
    if not created and instance.status == 'COMPLETED':
        # Use organization name as the audit identifier
        org_name = instance.organization.name if instance.organization else 'Unknown Organization'
        subject = f"Audit Completed: {org_name}"
        message = (
            f"Hello,\n\n"
            f"The audit for organization '{org_name}' has been successfully completed.\n\n"
            f"Audit ID: {instance.id}\n"
            f"Status: {instance.status}\n"
            f"Created: {instance.created_at}\n\n"
            f"View it here: https://zpie.co.in/audits/{instance.id}"
        )
        
        # Get the organization owner to send notification
        recipient_list = []
        if instance.organization and instance.organization.owner:
            recipient_list = [instance.organization.owner.email]
        
        if not recipient_list:
            # Skip sending if no recipient
            print(f"No recipient found for Audit {instance.id}")
            return
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                recipient_list,
                fail_silently=False,
            )
            print(f"Notification sent for Audit {instance.id}")
        except Exception as e:
            print(f"Failed to send email: {e}")

