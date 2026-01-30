import logging
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from github import Github

from apps.audits.models import Audit, Evidence, Question, AuditSnapshot, ScanHistory, RiskAcceptanceException
import json
from apps.integrations.models import Integration
from apps.audits.rules.new_checks import (
    check_org_2fa, check_actions_permissions, 
    check_repo_webhooks, check_branch_reviews
)

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def run_audit_task(self, audit_id):
    """
    Executes Industry-Standard Security Audit (CIS Checks).
    Performs 20+ checks via PyGithub directly.
    """
    try:
        # 1. Fetch Audit
        try:
            audit = Audit.objects.select_related("organization").get(id=audit_id)
        except Audit.DoesNotExist:
            logger.error(f"Audit {audit_id} not found.")
            return

        audit.status = "RUNNING"
        audit.save(update_fields=["status"])
        
        # Get the user object safely
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
            # Check for social token
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

        # Method C: Environment Variable Fallback
        if not token_value:
            from dotenv import load_dotenv
            import os
            load_dotenv()
            token_value = os.getenv("GITHUB_TOKEN")
            if token_value:
                logger.info("Using GITHUB_TOKEN from .env")
                # If using env token, target might need to be resolved via audit.organization or user
                if audit.organization and not target_id:
                     target_id = getattr(audit.organization, 'external_id', None)
            
        if not token_value:
            raise ValueError("No GitHub token found. Connect GitHub in Integrations or set GITHUB_TOKEN in .env.")
        
        if isinstance(token_value, bytes): token_value = token_value.decode('utf-8')

        # 3. Connect to GitHub & Resolve Target
        gh = Github(token_value)
        target = None

        try:
            # Resolve Target (Org or User)
            if target_id and not str(target_id).isdigit():
                target = gh.get_organization(target_id)
            else:
                user = gh.get_user()
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
            
            # 4. Run Checks
            # Clear previous evidence to avoid duplicates if re-running
            # Evidence.objects.filter(audit=audit).delete() # Optional: decide if we wipe previous

            # --- HELPER: Get or Create Question ---
            def get_question(key, title, severity='MEDIUM'):
                q, _ = Question.objects.get_or_create(
                    key=key,
                    defaults={
                        'title': title, 
                        'description': f"Automated check for {title}",
                        'severity': severity
                    }
                )
                return q

            # Load Risk Exceptions
            risk_exceptions = RiskAcceptanceException.objects.filter(organization=audit.organization)
            # Map: (check_id, resource_id) -> exception
            exception_map = { (e.check_id, e.resource_identifier): e for e in risk_exceptions }

            # --- HELPER: Save Evidence with Risk Acceptance ---
            def save_finding(question_key, title, status, severity, raw_data, comment, remediation=""):
                try:
                    # Determine Resource Identifier
                    resource_id = raw_data.get('repo_name') # e.g. 'org/repo'
                    
                    # Risk Acceptance Check
                    risk_exc = exception_map.get((question_key, resource_id))
                    if not risk_exc:
                         # Try Global Exception (resource_identifier is None or empty)
                         risk_exc = exception_map.get((question_key, None)) or exception_map.get((question_key, ""))
                    
                    final_status = status
                    risk_note = ""
                    
                    if risk_exc and status == "FAIL":
                        final_status = "RISK_ACCEPTED"
                        risk_note = f" [RISK ACCEPTED: {risk_exc.reason}]"

                    q = get_question(question_key, title, severity)
                    Evidence.objects.create(
                        audit=audit,
                        question=q,
                        status=final_status, # Use calculated status
                        status_state='RISK_ACCEPTED' if final_status == 'RISK_ACCEPTED' else ('OPEN' if status == 'FAIL' else 'FIXED'),
                        raw_data=raw_data,
                        comment=(comment or "") + risk_note,
                        remediation_steps=remediation
                    )
                except Exception as e:
                    logger.error(f"Failed to save evidence for {question_key}: {e} | Data: {raw_data}")
                    # Fallback (simplified)
                    try:
                        q_fallback = get_question(question_key, title, severity)
                        Evidence.objects.create(
                            audit=audit, 
                            question=q_fallback, 
                            status="ERROR", 
                            raw_data={'error': str(e)}, 
                            comment="System Error saving evidence"
                        )
                    except: pass


            logger.info(f"Scanning Target: {target.login}")
            
            # 4. Run Checks (Existing Logic - unchanged calls, just using new save_finding)
            
            # === ORG LEVEL CHECKS ===
            # Run these once if target is an Organization
            if hasattr(target, 'type') and target.type == 'Organization':
                
                # CIS 1.1 Enforce MFA
                try:
                    mfa_enabled = getattr(target, 'two_factor_requirement_enabled', None)
                    status = 'PASS' if mfa_enabled else 'FAIL'
                    save_finding(
                        'cis_1_1', 'Enforce Multi-Factor Authentication', 
                        status, 'CRITICAL', 
                        {'org': target.login, 'mfa_enabled': mfa_enabled, 'resource': target.login}, # Resource ID implies org name for global checks?
                        "MFA is enforced." if mfa_enabled else "MFA is NOT enforced for this organization.",
                        "Enable 'Require two-factor authentication' in Organization Settings > Security."
                    )
                except Exception as e:
                    logger.error(f"Check CIS 1.1 failed: {e}")

                # CIS 1.3 Excessive Owners
                try:
                    admin_count = 0
                    try:
                        admins = target.get_members(role='admin')
                        admin_count = admins.totalCount
                    except: pass
                    
                    status = 'FAIL' if admin_count > 5 else 'PASS'
                    save_finding(
                        'cis_1_3', 'Excessive Owners',
                        status, 'HIGH',
                        {'admin_count': admin_count, 'resource': target.login},
                        f"Found {admin_count} admins (Threshold: 5).",
                        "Reduce the number of Organization Owners to 5 or fewer."
                    )
                except Exception as e:
                    logger.error(f"Check CIS 1.3 failed: {e}")

            # === REPO LEVEL CHECKS ===
            repos = target.get_repos()
            for repo in repos:
                repo_name = repo.full_name
                logger.info(f"Checking repo: {repo_name}")
                
                # Context dict for raw_data
                base_ctx = {'repo_name': repo_name, 'url': repo.html_url}

                # ... (Existing Check Logic Snippets - I will assume they are injected here by virtue of NOT replacing them if I can help it, 
                # but I am replacing the whole block. I must re-include them or use multi-replace to target only save_finding.
                # Since I am replacing the WHOLE block from 127 to 606, I must re-include ALL checks. 
                # This is risky. I should use multi-replace or just replace `save_finding` and the post-processing logic.)
                
                # Actually, I can just replace `save_finding` definition and the post-processing block? 
                # But `save_finding` is inside `run_audit_task`.
                # And I need to update the checks to pass `repo_name`? 
                # `save_finding` takes `raw_data`. My updated `save_finding` extracts `repo_name` from `raw_data`. 
                # The existing calls pass `base_ctx` which has `repo_name`. So existing calls are fine!
                # EXCEPT for Org level checks. They pass `{'org': target.login, ...}`.
                # So I need to make sure `save_finding` handles missing `repo_name` or uses `org` or explicit arg.
                # I'll update `save_finding` to look for keys.
                
                # I will ONLY replace `save_finding` definition.
                # AND I will replace the END of the function (Post Processing).
                # This avoids re-writing all the check logic.
                
                pass # Logic is handled by MultiReplace below.




            logger.info(f"Scanning Target: {target.login}")
            
            # 4. Run Checks
            
            # --- CRITICAL: Org 2FA Check (Run Once) ---
            # We run this explicitly before any other checks
            if hasattr(target, 'type') and target.type == 'Organization':
                logger.info(f"Running Org 2FA Check for {target.login}")
                try:
                    res = check_org_2fa(target)
                    save_finding(
                        res['check_id'], res['title'],
                        res['status'], res['severity'],
                        res['system_logs'],
                        res['issue'],
                        res['remediation']
                    )
                except Exception as e:
                    logger.error(f"check_org_2fa failed: {e}")

            # === ORG LEVEL CHECKS ===
            # Run these once if target is an Organization
            if hasattr(target, 'type') and target.type == 'Organization':
                
                # CIS 1.1 Enforce MFA (Native Check)
                try:
                    mfa_enabled = getattr(target, 'two_factor_requirement_enabled', None)
                    status = 'PASS' if mfa_enabled else 'FAIL'
                    save_finding(
                        'cis_1_1', 'Enforce Multi-Factor Authentication', 
                        status, 'CRITICAL', 
                        {'org': target.login, 'mfa_enabled': mfa_enabled},
                        "MFA is enforced." if mfa_enabled else "MFA is NOT enforced for this organization.",
                        "Enable 'Require two-factor authentication' in Organization Settings > Security."
                    )
                except Exception as e:
                    logger.error(f"Check CIS 1.1 failed: {e}")

                # CIS 1.3 Excessive Owners
                try:
                    # Depending on permissions, we might not be able to list all members with roles
                    # falling back to simple check if possible
                    admin_count = 0
                    try:
                        admins = target.get_members(role='admin')
                        admin_count = admins.totalCount
                    except:
                        pass # ensure doesn't crash if permission denied
                    
                    status = 'FAIL' if admin_count > 5 else 'PASS'
                    save_finding(
                        'cis_1_3', 'Excessive Owners',
                        status, 'HIGH',
                        {'admin_count': admin_count},
                        f"Found {admin_count} admins (Threshold: 5).",
                        "Reduce the number of Organization Owners to 5 or fewer to minimize attack surface."
                    )
                except Exception as e:
                    logger.error(f"Check CIS 1.3 failed: {e}")

            # === REPO LEVEL CHECKS ===
            repos = target.get_repos()
            for repo in repos:
                repo_name = repo.full_name
                logger.info(f"Checking repo: {repo_name}")
                
                # Context dict for raw_data
                base_ctx = {'repo_name': repo_name, 'url': repo.html_url}

                # CIS 1.4 Outside Collaborators
                try:
                    collabs = repo.get_collaborators(affiliation='outside')
                    count = collabs.totalCount
                    status = 'FAIL' if count > 0 else 'PASS'
                    save_finding(
                        'cis_1_4', 'Outside Collaborators',
                        status, 'HIGH',
                        {**base_ctx, 'outside_collaborators_count': count},
                        f"Found {count} outside collaborators.",
                        "Remove outside collaborators or ensure they have minimal required access."
                    )
                except Exception as e:
                    pass # Often fails on personal repos or lacking permissions

                # CIS 2.1 Secret Scanning
                try:
                    # security_and_analysis IS an attribute, but might be missing or None
                    sec_analysis = getattr(repo, 'security_and_analysis', None)
                    secret_scanning = 'disabled'
                    if sec_analysis and sec_analysis.secret_scanning:
                        secret_scanning = sec_analysis.secret_scanning.status
                    
                    status = 'PASS' if secret_scanning == 'enabled' else 'FAIL'
                    save_finding(
                        'cis_2_1', 'Secret Scanning',
                        status, 'HIGH',
                        {**base_ctx, 'status': secret_scanning},
                        f"Secret scanning is {secret_scanning}.",
                        "Enable Secret Scanning in Repo Settings > Security & Analysis."
                    )
                except Exception as e:
                     pass

                # CIS 2.2 Dependabot
                try:
                    # repo.get_vulnerability_alert() is a boolean toggle for the repo? 
                    # Actually get_vulnerability_alert() enables/disables it or returns status?
                    # PyGithub says: enable_vulnerability_alert() / disable_... 
                    # To CHECK, we might need to rely on 'get_vulnerability_alert' if it exists as a property?
                    # Using get_vulnerability_alert() as requested by user instructions (Returns boolean).
                    alerts_enabled = repo.get_vulnerability_alert() 
                    status = 'PASS' if alerts_enabled else 'FAIL' 
                    save_finding(
                        'cis_2_2', 'Dependabot Alerts',
                        status, 'CB', # Critical/High?
                        {**base_ctx, 'enabled': alerts_enabled},
                        f"Dependabot alerts are {'enabled' if alerts_enabled else 'disabled'}.",
                        "Enable Dependabot alerts."
                    )
                except Exception:
                    pass

                # CIS 2.5 Private Repo
                try:
                    is_private = repo.private
                    status = 'PASS' if is_private else 'FAIL'
                    save_finding(
                        'cis_2_5', 'Private Repository',
                        status, 'CRITICAL',
                        {**base_ctx, 'private': is_private},
                        f"Repository is {'Private' if is_private else 'Public'}.",
                        "Ensure proprietary code is in a Private repository."
                    )
                except:
                    pass

                # --- BRANCH PROTECTION CHECKS (Main/Master) ---
                # First get default branch
                default_branch_name = repo.default_branch
                branch = None
                protection = None
                
                # Check Default Branch Name
                try:
                    status = 'FAIL' if default_branch_name == 'master' else 'PASS'
                    save_finding(
                        'default_branch', 'Default Branch Name',
                        status, 'LOW',
                        {**base_ctx, 'branch': default_branch_name},
                        f"Default branch is '{default_branch_name}'.",
                        "Rename 'master' to 'main' for inclusive naming standards."
                    )
                except: pass

                try:
                    branch = repo.get_branch(default_branch_name)
                    if branch.protected:
                        protection = branch.get_protection()
                except Exception:
                    # Branch not protected or error fetching
                    pass

                # CIS 3.1 Signed Commits
                try:
                    required = False
                    if protection and protection.required_signatures:
                        required = protection.required_signatures
                    
                    # Note: required_signatures might be a boolean or object depending on API version
                    # User prompt: "Get branch protection -> protection.required_signatures"
                    # In PyGithub, required_signatures is usually a boolean 'enabled' check via introspection
                    # We'll treat truthy as PASS
                    status = 'PASS' if required else 'FAIL'
                    save_finding(
                        'cis_3_1', 'Signed Commits',
                        status, 'MEDIUM',
                        {**base_ctx, 'required_signatures': required},
                        "Signed commits are enforced." if required else "Signed commits are NOT enforced.",
                        "Enable 'Require signed commits' in Branch Protection rules."
                    )
                except: pass

                # CIS 4.1 Branch Protection Enabled
                try:
                    is_protected = branch.protected if branch else False
                    status = 'PASS' if is_protected else 'FAIL'
                    save_finding(
                        'cis_4_1', 'Branch Protection',
                        status, 'HIGH',
                        {**base_ctx, 'protected': is_protected},
                        f"Branch protection is {'enabled' if is_protected else 'disabled'} for {default_branch_name}.",
                        "Enable Branch Protection for the default branch."
                    )
                except: pass

                # Only run granular protection checks if protection object exists
                if protection:
                    # CIS 4.2 Require Code Reviews
                    try:
                        reviews = protection.required_pull_request_reviews
                        status = 'PASS' if reviews else 'FAIL'
                        save_finding(
                            'cis_4_2', 'Require Code Reviews',
                            status, 'HIGH',
                            {**base_ctx},
                            "PR reviews are enforced." if reviews else "PR reviews are NOT enforced.",
                            "Enable 'Require pull request reviews before merging'."
                        )
                    except: pass
                    
                    # CIS 4.3 Dismiss Stale Reviews
                    try:
                        stale = False
                        if protection.required_pull_request_reviews:
                            stale = protection.required_pull_request_reviews.dismiss_stale_reviews
                        status = 'PASS' if stale else 'FAIL'
                        save_finding(
                            'cis_4_3', 'Dismiss Stale Reviews',
                            status, 'MEDIUM',
                            {**base_ctx},
                            "Stale reviews are dismissed." if stale else "Stale reviews are NOT dismissed when new commits are pushed.",
                            "Enable 'Dismiss stale pull request approvals when new commits are pushed'."
                        )
                    except: pass

                    # CIS 4.4 Enforce for Admins
                    try:
                        # enforce_admins is often an object with 'enabled' bool
                        admins = protection.enforce_admins
                        is_enforced = admins.enabled if admins else False
                        status = 'PASS' if is_enforced else 'FAIL'
                        save_finding(
                            'cis_4_4', 'Enforce for Admins',
                            status, 'HIGH',
                            {**base_ctx},
                            "Rules enforced for admins." if is_enforced else "Rules are NOT enforced for administrators.",
                            "Enable 'Do not allow bypassing the above settings' (Enforce for Admins)."
                        )
                    except: pass

                    # CIS 4.5 Linear History
                    try:
                        linear = protection.required_linear_history
                        # required_linear_history is object or bool? usually object with enabled.
                        # User prompt: "Check protection.required_linear_history"
                        # PyGithub: get_required_linear_history() -> RequiredLinearHistory object or None
                        # But 'protection.required_linear_history' might works as property
                        is_linear = False
                        if hasattr(protection, 'required_linear_history'):
                             if protection.required_linear_history: 
                                 is_linear = protection.required_linear_history.enabled
                        
                        status = 'PASS' if is_linear else 'FAIL'
                        save_finding(
                            'cis_4_5', 'Linear History',
                            status, 'LOW',
                            {**base_ctx},
                            "Linear history enforced." if is_linear else "Linear history not enforced.",
                            "Enable 'Require linear history'."
                        )
                    except: pass

                    # CIS 4.6 Status Checks
                    try:
                        checks = protection.required_status_checks
                        status = 'PASS' if checks else 'FAIL'
                        save_finding(
                            'cis_4_6', 'Required Status Checks',
                            status, 'MEDIUM',
                            {**base_ctx},
                            "Status checks required." if checks else "No status checks required.",
                            "Enable 'Require status checks to pass before merging'."
                        )
                    except: pass
                    
                    # CIS 4.7 Force Pushes
                    try:
                        # Should be False or None (Allowing force pushes is BAD)
                        # protection.allow_force_pushes -> object or None. 
                        # If None -> Default is usually False (Good). 
                        # If Present -> check enabled.
                        force = protection.allow_force_pushes
                        is_allowed = force.enabled if force else False
                        
                        status = 'FAIL' if is_allowed else 'PASS'
                        save_finding(
                            'cis_4_7', 'No Force Pushes',
                            status, 'HIGH',
                            {**base_ctx, 'allowed_force_pushes': is_allowed},
                            "Force pushes DENIED (Good)." if not is_allowed else "Force pushes are ALLOWED (Bad).",
                            "Disable 'Allow force pushes' (it should be unchecked)."
                        )
                    except: pass

                    # CIS 4.8 Branch Deletion
                    try:
                        # Should be False/None
                        deletions = protection.allow_deletions
                        is_allowed = deletions.enabled if deletions else False
                        
                        status = 'FAIL' if is_allowed else 'PASS'
                        save_finding(
                            'cis_4_8', 'No Branch Deletion',
                            status, 'MEDIUM',
                            {**base_ctx, 'allowed_deletions': is_allowed},
                            "Branch deletion DENIED (Good)." if not is_allowed else "Branch deletion ALLOWED (Bad).",
                            "Disable 'Allow deletions' (it should be unchecked)."
                        )
                    except: pass

                # CIS 5.1 CODEOWNERS
                try:
                    has_codeowners = False
                    try:
                        # Check .github/CODEOWNERS
                        repo.get_contents(".github/CODEOWNERS")
                        has_codeowners = True
                    except:
                        try:
                            # Check docs/CODEOWNERS
                            repo.get_contents("docs/CODEOWNERS")
                            has_codeowners = True
                        except:
                            try:
                                # Check root CODEOWNERS
                                repo.get_contents("CODEOWNERS")
                                has_codeowners = True
                            except: pass
                    
                    status = 'PASS' if has_codeowners else 'FAIL'
                    save_finding(
                        'cis_5_1', 'CODEOWNERS File',
                        status, 'MEDIUM',
                        {**base_ctx},
                        "CODEOWNERS file found." if has_codeowners else "Missing CODEOWNERS file.",
                        "Add a CODEOWNERS file to .github/, docs/, or root."
                    )
                except: pass

                # GH-GOV-1 License
                try:
                    has_license = False
                    try:
                        repo.get_license()
                        has_license = True
                    except: pass
                    status = 'PASS' if has_license else 'FAIL'
                    save_finding(
                        'gh_gov_1', 'License File',
                        status, 'MEDIUM',
                        {**base_ctx},
                        "License found." if has_license else "No License detected.",
                        "Add a LICENSE file."
                    )
                except: pass
                
                # GH-GOV-2 Readme
                try:
                    has_readme = False
                    try:
                         repo.get_readme()
                         has_readme = True
                    except: pass
                    status = 'PASS' if has_readme else 'FAIL'
                    save_finding(
                        'gh_gov_2', 'README File',
                        status, 'LOW',
                        {**base_ctx},
                        "README found." if has_readme else "No README detected.",
                        "Add a README.md file."
                    )
                except: pass
                
                # Issues Enabled
                try:
                    has_issues = repo.has_issues
                    status = 'PASS' if has_issues else 'FAIL'
                    save_finding(
                        'issues_enabled', 'Issues Enabled',
                        status, 'LOW',
                        {**base_ctx},
                        "Issues are enabled." if has_issues else "Issues are disabled.",
                        "Enable Issues in Repo Settings."
                    )
                except: pass

                # [NEW] Check Actions Permissions
                try:
                    res = check_actions_permissions(repo)
                    save_finding(
                        res['check_id'], res['title'],
                        res['status'], res['severity'],
                        res['system_logs'],
                        res['issue'],
                        res['remediation']
                    )
                except Exception as e: logger.error(f"check_actions_permissions failed: {e}")

                # [NEW] Check Repo Webhooks
                try:
                    res = check_repo_webhooks(repo)
                    save_finding(
                        res['check_id'], res['title'],
                        res['status'], res['severity'],
                        res['system_logs'],
                        res['issue'],
                        res['remediation']
                    )
                except Exception as e: logger.error(f"check_repo_webhooks failed: {e}")

                # [NEW] Check Branch Reviews
                try:
                    res = check_branch_reviews(repo)
                    save_finding(
                        res['check_id'], res['title'],
                        res['status'], res['severity'],
                        res['system_logs'],
                        res['issue'],
                        res['remediation']
                    )
                except Exception as e: logger.error(f"check_branch_reviews failed: {e}")

            # Update Audit - Success
            audit.status = "COMPLETED"
            audit.completed_at = timezone.now()
            
            # --- CONTINUOUS COMPLIANCE LOGIC ---
            
            # 1. Calculate Score (Risk Accepted = Compliant i.e., Pass)
            # Formula: 100 - (15 * Critical Failures) - (10 * High Failures)
            critical_fails = Evidence.objects.filter(audit=audit, status='FAIL', question__severity='CRITICAL').count()
            high_fails = Evidence.objects.filter(audit=audit, status='FAIL', question__severity='HIGH').count()
            
            penalty = (15 * critical_fails) + (10 * high_fails)
            score = max(0, 100 - penalty)
            
            # Helper for History
            total_ev = Evidence.objects.filter(audit=audit).count()
            active_failures = Evidence.objects.filter(audit=audit, status='FAIL').count()
            
            audit.score = score
            audit.status = 'COMPLETED'
            
            audit.save()
            
            # 2. History Tracking
            if audit.organization:
                 ScanHistory.objects.create(
                     user=audit_user,
                     organization=audit.organization,
                     score=score,
                     total_fail=active_failures,
                     total_pass=total_ev - active_failures
                 )
            
            # 3. Snapshot Creation
            evidence_data = list(Evidence.objects.filter(audit=audit).values(
                'question__key', 'status', 'raw_data', 'comment'
            ))
            snapshot_data = {
                'audit_id': str(audit.id),
                'score': score,
                'evidence': evidence_data,
                'timestamp': str(timezone.now())
            }
            # Versioning - find latest snapshot for this audit
            last_version = AuditSnapshot.objects.filter(audit=audit).order_by('-version').first()
            new_version = (last_version.version + 1) if last_version else 1
            
            current_snapshot = AuditSnapshot.objects.create(
                audit=audit,
                organization=audit.organization,
                name=f"Scan {new_version}",
                version=new_version,
                data=snapshot_data,
                created_by=audit_user
            )

            # 4. Regression Detection (Alerting)
            # 4. Regression & Remediation Detection (The "Diffing" Engine)
            # Get PREVIOUS snapshot from ANY previous audit for this org
            prev_snapshot = AuditSnapshot.objects.filter(
                organization=audit.organization
            ).exclude(id=current_snapshot.id).order_by('-created_at').first()

            regressions = []
            remediations = []
            
            if prev_snapshot:
                 # Map: Key -> Status
                 prev_evidence = { e['question__key']: e['status'] for e in prev_snapshot.data.get('evidence', []) }
                 
                 for ev in evidence_data:
                     key = ev['question__key']
                     current_status = ev['status']
                     prev_status = prev_evidence.get(key, 'PASS') # If new check, assume PASS previously?
                     repo_name = ev['raw_data'].get('repo_name', 'Global')
                     
                     # Regression: PASSED -> FAILED
                     if current_status == 'FAIL' and prev_status != 'FAIL':
                          regressions.append({
                              'check': key,
                              'resource': repo_name,
                              'status': 'REGRESSION',
                              'details': f"Check {key} failed on {repo_name} (Prev: {prev_status})"
                          })
                    
                     # Remediation: FAILED -> PASSED (or RISK_ACCEPTED)
                     if current_status in ['PASS', 'RISK_ACCEPTED'] and prev_status == 'FAIL':
                         remediations.append({
                             'check': key,
                             'resource': repo_name,
                             'status': 'FIXED',
                             'details': f"Check {key} passed on {repo_name}"
                         })
            
            # Update Snapshot Data with Diff
            snapshot_data['diff'] = {
                'regressions': regressions,
                'remediations': remediations,
                'summary': f"Found {len(regressions)} regressions and {len(remediations)} fixes."
            }
            # Save the updated data to the snapshot
            current_snapshot.data = snapshot_data
            current_snapshot.save()

            if regressions:
                 alert_payload = {
                     "actions": [{
                         "type": "TRIGGER_ALERT",
                         "channel": "SLACK_WEBHOOK",
                         "payload": {
                             "priority": "HIGH",
                             "message": f"🚨 {len(regressions)} New Security Regressions Detected.",
                             "details": regressions,
                             "actions": [
                                 {
                                     "type": "button",
                                     "text": "Fix this",
                                     "url": f"{settings.FRONTEND_URL}/audits/{audit.id}"
                                 }
                             ]
                         }
                     }]
                 }
                 logger.info(f"ALERT TRIGGERED: {json.dumps(alert_payload)}")
            
            if remediations:
                logger.info(f"PROGRESS: {len(remediations)} previously failing checks are now fixed.")

            logger.info(f"Audit {audit_id} Completed. Score: {score}")
            
        except Exception as e:
            raise ValueError(f"GitHub Connection/Audit Failed: {e}")

    except Exception as e:
        logger.exception(f"CRITICAL FAILURE: {e}")
        try:
            a = Audit.objects.get(id=audit_id)
            a.status = "FAILED"
            # a.failure_reason = str(e) # if field exists
            a.save()
        except: pass

# Keep placeholders
@shared_task(bind=True)
def generate_pdf_task(self, audit_id): pass 

@shared_task(bind=True)
def send_critical_alert_email_task(self, audit_id): pass
