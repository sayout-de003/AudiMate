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

    Responsibilities:
    - Connect to GitHub securely
    - Execute organization + repository rules
    - Persist evidence atomically
    - Maintain strict audit lifecycle
    """

    try:
        audit = Audit.objects.select_related("organization").get(id=audit_id)

        if audit.status not in ["PENDING", "FAILED"]:
            logger.warning(f"Audit {audit_id} already executed or running")
            return {"status": "Skipped", "reason": "Invalid audit state"}

        audit.status = "RUNNING"
        audit.save(update_fields=["status"])

        # Clear previous evidence (idempotency)
        Evidence.objects.filter(audit=audit).delete()

        token = audit.organization.get_token()
        github = Github(token)

        try:
            gh_org = github.get_organization(audit.organization.github_org_name)
        except GithubException as e:
            raise RuntimeError(f"GitHub org access failed: {str(e)}")

        evidence_to_create = []

        # -------------------------------
        # Organization-level rules
        # -------------------------------
        org_rules = [
            EnforceMFA(),
            StaleAdminAccess(),
            ExcessiveOwners(),
        ]

        for rule in org_rules:
            evidence_to_create.append(
                _execute_rule(
                    audit=audit,
                    rule=rule,
                    context=gh_org,
                    resource_name=audit.organization.name
                )
            )

        # -------------------------------
        # Repository-level rules
        # -------------------------------
        repo_rules = [
            SecretScanningEnabled(),
            DependabotEnabled(),
            PrivateRepoVisibility(),
            EnforceSignedCommits(),
            BranchProtectionMain(),
            RequireCodeReviews(),
            DismissStaleReviews(),
            RequireLinearHistory(),
            CodeOwnersExist(),
        ]

        for repo in gh_org.get_repos():
            if repo.archived:
                continue

            for rule in repo_rules:
                evidence_to_create.append(
                    _execute_rule(
                        audit=audit,
                        rule=rule,
                        context=repo,
                        resource_name=repo.name
                    )
                )

        # -------------------------------
        # Persist evidence atomically
        # -------------------------------
        with transaction.atomic():
            Evidence.objects.bulk_create(
                [e for e in evidence_to_create if e is not None],
                ignore_conflicts=True
            )

            audit.status = "COMPLETED"
            audit.completed_at = timezone.now()
            audit.save(update_fields=["status", "completed_at"])

        return {"status": "COMPLETED", "audit_id": str(audit.id)}

    except Exception as e:
        logger.exception(f"Audit {audit_id} failed")

        try:
            audit.status = "FAILED"
            audit.save(update_fields=["status"])
        except Exception:
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
