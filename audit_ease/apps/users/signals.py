from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from apps.organizations.models import Organization, Membership
from apps.audits.models import Audit
from apps.audits.tasks import run_audit_task
import logging
from django.db import transaction

logger = logging.getLogger(__name__)

@receiver(user_signed_up)
def handle_onboarding_magic(request, user, **kwargs):
    """
    Onboarding Magic:
    1. Create default Organization if missing.
    2. Immediately start an audit scan.
    """
    logger.info(f"Onboarding Magic triggered for {user.email}")
    
    try:
        with transaction.atomic():
            # 1. Check/Create Organization
            # Usually handled by other signals but we enforce here for safety
            organization = user.get_organization()
            if not organization:
                org_name = f"{user.username}'s Organization"
                organization = Organization.objects.create(
                    name=org_name,
                    owner=user,
                    subscription_plan=Organization.SUBSCRIPTION_PLAN_FREE,
                    subscription_status=Organization.SUBSCRIPTION_STATUS_FREE
                )
                Membership.objects.create(
                    user=user,
                    organization=organization,
                    role=Membership.ROLE_ADMIN
                )
                logger.info(f"Created default organization for {user.email}")

            # 2. Start 'Welcome Scan'
            audit = Audit.objects.create(
                organization=organization,
                triggered_by=user,
                status='PENDING'
            )
            
            # 3. Trigger Async Task
            run_audit_task.delay(audit.id)
            
            logger.info(f"Started Welcome Scan (Audit {audit.id}) for {user.email}")

    except Exception as e:
        logger.error(f"Onboarding Magic failed for {user.email}: {e}")
