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
        audit = Audit.objects.select_related("organization", "triggered_by").get(id=audit_id)
        audit.status = "RUNNING"
        audit.save(update_fields=["status"])

        # 1. Fetch Integration to get Org Name
        try:
            integration = Integration.objects.get(
                organization=audit.organization,
                provider=Integration.ProviderChoices.GITHUB
            )
            github_org_name = integration.external_id
        except Integration.DoesNotExist:
            audit.status = "FAILED"
            audit.save()
            return {"status": "FAILED", "reason": "No GitHub Integration found"}

        # 2. List Repositories (We need a client to list them first)
        # We can use the Scanner's method if we expose it, or just use PyGithub directly here for listing
        # Ideally, we rely on the one passed in user's token.
        
        # Helper to get client just for listing
        try:
            scanner_for_listing = GitHubScanner(audit.triggered_by, "dummy/repo")
            gh_client = scanner_for_listing.github
            org = gh_client.get_organization(github_org_name)
            repos = org.get_repos()
        except Exception as e:
            logger.error(f"Failed to list repos for {github_org_name}: {e}")
            audit.status = "FAILED"
            audit.save()
            return {"status": "FAILED", "reason": f"GitHub API Error: {str(e)}"}

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
                scanner = GitHubScanner(audit.triggered_by, repo.full_name)
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
        audit.status = "FAILED"
        audit.save(update_fields=["status"])
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
            f"Dashboard Link: https://audit-ease.com/dashboard/audits/{audit_id}/" # Replace with actual domain if known, else use relative or prompt user
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
