import logging
from celery import shared_task
from django.utils import timezone
from github import Github

from apps.audits.models import Audit, Evidence, Question
from apps.integrations.models import Integration

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def run_audit_task(self, audit_id):
    """
    Executes Industry-Standard Security Audit (CIS Checks).
    """
    try:
        # 1. Fetch Audit
        try:
            # Try to fetch with related fields, handle 'user' vs 'triggered_by' dynamically later
            audit = Audit.objects.select_related("organization").get(id=audit_id)
        except Audit.DoesNotExist:
            logger.error(f"Audit {audit_id} not found.")
            return

        audit.status = "RUNNING"
        audit.save(update_fields=["status"])
        
        # Get the user object safely (handle both naming conventions)
        audit_user = getattr(audit, 'user', getattr(audit, 'triggered_by', None))
        
        logger.info(f"--- Starting Audit {audit_id} for Org: {audit.organization} ---")

        # 2. Authentication Logic
        token_value = None
        target_id = None

        # Method A: Organization Integration (Preferred)
        if audit.organization:
            integration = Integration.objects.filter(
                organization=audit.organization,
                provider='github'
            ).first()
            
            if integration and integration.access_token:
                token_value = integration.access_token
                target_id = integration.external_id
                logger.info("Using Organization Integration Token.")

        # Method B: User Token Fallback
        if not token_value and audit_user:
            from allauth.socialaccount.models import SocialToken
            logger.info(f"Checking User Token for: {audit_user}")
            social_token = SocialToken.objects.filter(
                account__user=audit_user, 
                app__provider='github'
            ).first()
            if social_token:
                token_value = social_token.token
                # Use Org ID if available, otherwise User ID
                if audit.organization:
                    target_id = getattr(audit.organization, 'external_id', str(audit.organization.id))
                else:
                    target_id = str(audit_user.username)
                logger.info("Using User Fallback Token.")

        if not token_value:
            raise ValueError("No GitHub token found. Connect GitHub in Integrations.")
        
        if isinstance(token_value, bytes): token_value = token_value.decode('utf-8')

        # 3. Connect to GitHub & Resolve Target
        gh = Github(token_value)
        target = None

        try:
            # If target_id looks like a name (e.g. "alienhousenetworks")
            if target_id and not str(target_id).isdigit():
                target = gh.get_organization(target_id)
            # If target_id is numeric or missing
            else:
                user = gh.get_user()
                # Check if we are scanning the user themselves
                if not target_id or str(user.id) == str(target_id):
                    target = user
                else:
                    # Search user's orgs for the numeric ID
                    found = False
                    for org in user.get_orgs():
                        if str(org.id) == str(target_id):
                            target = org
                            found = True
                            break
                    target = target if found else gh.get_organization(int(target_id))
            
            logger.info(f"Scanning Target: {target.login}")
            repos = target.get_repos()
            
        except Exception as e:
            raise ValueError(f"GitHub Connection Failed: {e}")

        # 4. Run Checks
        # Clear old evidence
        Evidence.objects.filter(audit=audit).delete()
        
        # Define Questions
        q_private, _ = Question.objects.get_or_create(key="repo_private", defaults={"title": "Repo Visibility", "severity": "CRITICAL"})
        q_branch, _ = Question.objects.get_or_create(key="branch_protected", defaults={"title": "Branch Protection", "severity": "HIGH"})
        q_readme, _ = Question.objects.get_or_create(key="readme_exists", defaults={"title": "Documentation", "severity": "MEDIUM"})

        findings_count = 0
        repo_count = 0

        for repo in repos:
            if repo.archived: continue
            repo_count += 1
            
            # Check 1: Visibility
            try:
                is_private = repo.private
                Evidence.objects.create(
                    audit=audit, question=q_private,
                    status="PASS" if is_private else "FAIL",
                    raw_data={"repo": repo.full_name},
                    comment=f"{repo.full_name} is {'Private' if is_private else 'Public'}."
                )
                if not is_private: findings_count += 1
            except Exception as e:
                logger.error(f"Check 1 Error: {e}")

            # Check 2: Branch Protection
            try:
                is_protected = False
                if repo.default_branch:
                    try:
                        is_protected = repo.get_branch(repo.default_branch).protected
                    except: pass # Branch might not exist or 404
                
                Evidence.objects.create(
                    audit=audit, question=q_branch,
                    status="PASS" if is_protected else "FAIL",
                    raw_data={"repo": repo.full_name, "branch": repo.default_branch},
                    comment=f"Default branch protection: {is_protected}"
                )
                if not is_protected: findings_count += 1
            except Exception as e:
                logger.error(f"Check 2 Error: {e}")

            # Check 3: Readme
            try:
                has_readme = False
                try:
                    repo.get_readme()
                    has_readme = True
                except: pass
                
                Evidence.objects.create(
                    audit=audit, question=q_readme,
                    status="PASS" if has_readme else "FAIL",
                    raw_data={"repo": repo.full_name},
                    comment=f"{'Readme found.' if has_readme else 'Readme missing.'}"
                )
                if not has_readme: findings_count += 1
            except Exception as e:
                logger.error(f"Check 3 Error: {e}")

        # 5. Score & Save
        deduction = findings_count * 5
        score = max(0, 100 - deduction)

        audit.score = score
        audit.status = "COMPLETED"
        audit.completed_at = timezone.now()
        audit.save()
        
        logger.info(f"Audit {audit_id} COMPLETED. Score: {score}")
        return {"status": "COMPLETED", "score": score}

    except Exception as e:
        logger.exception(f"CRITICAL FAILURE: {e}")
        try:
            a = Audit.objects.get(id=audit_id)
            a.status = "FAILED"
            a.failure_reason = str(e)
            a.save()
        except: pass

# Keep placeholders
@shared_task(bind=True)
def generate_pdf_task(self, audit_id): pass 

@shared_task(bind=True)
def send_critical_alert_email_task(self, audit_id): pass
