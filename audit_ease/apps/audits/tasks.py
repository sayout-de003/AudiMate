import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from github import Github, GithubException

from .models import Audit, Evidence, Question
from .rules.cis_benchmark import (
    EnforceMFA, StaleAdminAccess, ExcessiveOwners,
    SecretScanningEnabled, DependabotEnabled, PrivateRepoVisibility,
    EnforceSignedCommits, BranchProtectionMain, RequireCodeReviews,
    DismissStaleReviews, RequireLinearHistory, CodeOwnersExist
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=60, retry_kwargs={"max_retries": 3})
def run_audit_task(self, audit_id):
    """
    Core audit execution task.
    ITERATES over all repositories in the linked GitHub Organization.
    """
    from apps.integrations.models import Integration
    from .services.scanner import GitHubScanner
    from django.db.models import Sum

    try:
        try:
            audit = Audit.objects.select_related("organization", "triggered_by").get(id=audit_id)
        except Audit.DoesNotExist:
            logger.warning(f"Audit {audit_id} not found. Stopping task to prevent retries (Audit likely deleted).")
            return {"status": "ABORTED", "reason": "Audit not found"}

        audit.status = "RUNNING"
        audit.save(update_fields=["status"])

    # 1. PRIORITY: Check for Organization Integration first
        if audit.organization:
            # Import Integration here or at top level. Keeping it local as per original style if preferred, 
            # but user asked for "MAKE SURE THIS IS IMPORTED". I will assume it is imported.
            # However, looking at the original file, it was imported inside the function.
            # I will assume `Integration` is available.
            # Re-importing just in case to be safe within this block if I don't move it to top,
            # but I should probably move the import to top level in a separate edit or just rely on the existing import at line 24.
            # Since I am replacing lines 30-something, I need to check where `Integration` is imported. 
            # It was at line 24. My replacement block starts later.
            
            logger.info(f"Checking integration for Org: {audit.organization.id}")
            integration = Integration.objects.filter(
                organization=audit.organization,
                provider=Integration.ProviderChoices.GITHUB
            ).first()

            if integration and integration.access_token:
                token_value = integration.access_token
                github_org_name = integration.external_id
                logger.info("Found Organization Token.")

        # 2. FALLBACK: Check for Personal User Token (SocialAccount)
        if not token_value:
            from allauth.socialaccount.models import SocialToken
            logger.info(f"No Org token. Checking User: {audit.user.id}")
            social_token = SocialToken.objects.filter(
                account__user=audit.user, 
                app__provider='github'
            ).first()
            if social_token:
                token_value = social_token.token
        if not token_value or not github_org_name:
            audit.status = "FAILED"
            audit.failure_reason = "No GitHub token or Organization found for Organization: " + str(audit.organization)
            audit.save()
            return {"status": "FAILED", "reason": "No GitHub token found"}
        
        # Ensure token is string if it's bytes
        if isinstance(token_value, bytes):
            token_value = token_value.decode('utf-8')

        gh_client = Github(token_value)
        
        try:
            # 1. Try fetching by string name first (if it's not a number)
            if not str(github_org_name).isdigit():
                 org = gh_client.get_organization(github_org_name)
            
            else:
                # 2. If it IS a number (like 248286261), we must find the correct object
                logger.info(f"Searching for Org ID {github_org_name} among user's orgs...")
                found_org = None
                
                # Check if the ID belongs to the authenticated user themselves (Personal Account)
                auth_user = gh_client.get_user()
                if str(auth_user.id) == str(github_org_name):
                    found_org = auth_user
                    logger.info(f"Resolved Org ID {github_org_name} -> Authenticated User: {auth_user.login}")
                
                if not found_org:
                    # Iterate over the authenticated user's organizations to match the ID
                    # This is safer than get_organization(id) which often fails with 404 on IDs
                    for org_obj in auth_user.get_orgs():
                        if str(org_obj.id) == str(github_org_name):
                            found_org = org_obj
                            break
                
                if found_org:
                    org = found_org
                    # Update the audit with the human-readable name for future reference
                    logger.info(f"Resolved Org ID {github_org_name} -> Name: {org.login}")
                else:
                    # Fallback: Try get_organization with the ID cast to int (rarely works but worth a shot)
                    org = gh_client.get_organization(int(github_org_name))

            repos = org.get_repos()
            logger.info(f"DEBUG: Successfully listed repos for {org.login}")

        except Exception as e:
            logger.exception(f"Failed to resolve Organization {github_org_name}")
            audit.status = "FAILED"
            audit.failure_reason = f"Could not access Organization: {str(e)}"
            audit.save()
            return {"status": "FAILED"}

        total_score = 100
        findings_count = 0
        
        # Clear previous evidence
        Evidence.objects.filter(audit=audit).delete()

        # Get Question
        try:
            readme_question = Question.objects.get(key="readme_exists")
        except Question.DoesNotExist:
            logger.error("Question 'readme_exists' not found in DB fixtures")
            # Create it on the fly if missing (safety net)
            readme_question = Question.objects.create(
                key="readme_exists",
                title="Missing Documentation",
                description="Checks if the repository has a README.md file.",
                severity="MEDIUM"
            )

        # 3. Iterate and Scan
        for repo in repos:
            if repo.archived:
                continue

            try:
                # FIXED: Use token_value instead of integration.access_token
                scanner = GitHubScanner(audit.triggered_by, repo.full_name, token=token_value)
                result = scanner.run_check()

                if not result["has_readme"]:
                    findings_count += 1
                    Evidence.objects.create(
                        audit=audit,
                        question=readme_question,
                        status="FAIL",
                        raw_data={"repo": repo.full_name, "details": result},
                        comment=f"Repository {repo.full_name} is missing a README.md file."
                    )
            except Exception as e:
                logger.error(f"Failed to scan repo {repo.full_name}: {e}")

        # 4. Calculate Score
        # Simple Logic: deduct 10 points per missing readme, min 0
        deduction = findings_count * 10
        final_score = max(0, 100 - deduction)

        audit.score = final_score
        audit.status = "COMPLETED"
        audit.completed_at = timezone.now()
        audit.save(update_fields=["status", "completed_at", "score"])

        return {"status": "COMPLETED", "audit_id": str(audit.id), "score": final_score}

    except Exception as e:
        logger.exception(f"Audit {audit_id} failed")
        try:
            # Only try to update status if we successfully fetched the audit object
            if 'audit' in locals():
                audit.status = "FAILED"
                audit.save(update_fields=["status"])
        except Exception:
            # If we can't update the status (e.g. DB error or audit not found), just ignore
            pass
        raise e


def _execute_rule(*, audit, rule, context, resource_name):
    """
    Executes a single rule safely and converts the result to Evidence.
    """

    try:
        question = Question.objects.get(key=rule.id)

        result = rule.check(context)

        return Evidence(
            audit=audit,
            question=question,
            status="PASS" if result.passed else "FAIL",
            raw_data=result.raw_data or {},
            comment=result.details
        )

    except Question.DoesNotExist:
        logger.error(f"Question missing for rule {rule.id}")
        return None

    except GithubException as e:
        logger.warning(f"GitHub API failure on rule {rule.id}: {e}")
        return Evidence(
            audit=audit,
            question=question,
            status="ERROR",
            raw_data={"error": str(e)},
            comment="GitHub API error during rule execution"
        )

    except Exception as e:
        logger.exception(f"Rule {rule.id} execution failed")
        return Evidence(
            audit=audit,
            question=question,
            status="ERROR",
            raw_data={"error": str(e)},
            comment="Internal rule execution error"
        )


@shared_task(bind=True)
def generate_pdf_task(self, audit_id):
    """
    Async placeholder for PDF generation.
    Should only be called for COMPLETED audits.
    """

    audit = Audit.objects.get(id=audit_id)

    if audit.status != "COMPLETED":
        raise ValueError("PDF can only be generated for completed audits")

    logger.info(f"PDF generation queued for audit {audit_id}")

    # Phase-4 hook
    # pdf_service = AuditPDFGenerator(audit)
    # pdf_service.generate()

    return {"status": "QUEUED", "audit_id": str(audit_id)}


@shared_task(bind=True)
def send_critical_alert_email_task(self, audit_id):
    """
    Sends an email alert to the organization owner if critical issues are found.
    """
    try:
        audit = Audit.objects.select_related('organization__owner').get(id=audit_id)
        
        # Double check if critical issues exist (sanity check)
        critical_count = Evidence.objects.filter(
            audit=audit, 
            status='FAIL', 
            question__severity='CRITICAL'
        ).count()

        if critical_count == 0:
            logger.info(f"No critical issues found for Audit {audit_id}. Skipping email.")
            return "Skipped (No Critical Issues)"

        organization = audit.organization
        if not organization or not organization.owner or not organization.owner.email:
            logger.warning(f"No owner email found for Organization {organization.id if organization else 'None'}")
            return "Skipped (No Owner Email)"

        owner_email = organization.owner.email
        org_name = organization.name
        repo_name = "your repositories"  # Default generic name
        # Try to infer repo name if possible, or just say "Organization Name"
        
        subject = f"🚨 ALERT: Critical Security Issues Found in {org_name}"
        
        body = (
            f"Your recent audit of {org_name} detected {critical_count} critical issues. "
            f"Please log in to your dashboard immediately to review these findings.\n\n"
            f"Dashboard Link: {settings.FRONTEND_URL}/dashboard/audits/{audit_id}/"
        )

        from django.core.mail import send_mail
        from django.conf import settings

        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [owner_email],
            fail_silently=False,
        )
        
        return f"Email sent to {owner_email}"

    except Audit.DoesNotExist:
        logger.error(f"Audit {audit_id} not found during email alert task")
        return "Failed (Audit Not Found)"
    except Exception as e:
        logger.exception(f"Failed to send critical alert email for Audit {audit_id}")
        # We might want to retry here depending on the error type
        raise e
