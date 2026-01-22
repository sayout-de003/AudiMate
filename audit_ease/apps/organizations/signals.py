"""
Organization Signals

Auto-create admin membership when organization is created.
This ensures the organization creator is always an admin.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
import logging

from .models import Organization, Membership

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Organization)
def auto_create_admin_membership(sender, instance, created, **kwargs):
    """
    Create ADMIN membership for organization owner.
    
    This signal is triggered after Organization.save() completes.
    We check 'created' flag to only run on creation, not updates.
    
    NOTE: The OrganizationSerializer already creates this membership
    in an atomic transaction during API creation, so this is a fallback
    for programmatic organization creation (e.g., management commands).
    
    To avoid duplicate membership errors, we check if it already exists.
    """
    if not created:
        # Only on creation, not on updates
        return
    
    # Check if membership already exists (likely created by serializer)
    if Membership.objects.filter(
        user=instance.owner,
        organization=instance
    ).exists():
        logger.debug(
            f"Membership already exists for {instance.owner.email} "
            f"in org {instance.name}, skipping auto-creation"
        )
        return
    
    # Create admin membership for owner (fallback for non-API creation)
    try:
        with transaction.atomic():
            membership = Membership.objects.create(
                user=instance.owner,
                organization=instance,
                role=Membership.ROLE_ADMIN
            )
            logger.info(
                f"Auto-created ADMIN membership for {instance.owner.email} "
                f"in organization {instance.name}"
            )
    except Exception as e:
        logger.error(
            f"Failed to create admin membership for {instance.owner.email}: {e}"
        )

