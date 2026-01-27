import logging

logger = logging.getLogger(__name__)

def check_org_2fa(org):
    """
    Check if Organization 2FA is required.
    Status: Critical
    """
    check_id = "org_2fa"
    title = "Organization Two-Factor Authentication"
    
    try:
        # Check if 2FA is required
        # Note: two_factor_requirement_enabled is a boolean on the Org object
        # We handle attribute verification to be safe
        mfa_enabled = False
        if hasattr(org, 'two_factor_requirement_enabled'):
            mfa_enabled = org.two_factor_requirement_enabled
        
        if mfa_enabled:
            return {
                "check_id": check_id,
                "title": title,
                "status": "PASS",
                "severity": "CRITICAL",
                "issue": "2FA is enforced.",
                "remediation": "",
                "system_logs": {"org": org.login, "mfa_enabled": True}
            }
        else:
            return {
                "check_id": check_id,
                "title": title,
                "status": "FAIL",
                "severity": "CRITICAL",
                "issue": "MFA is NOT enforced for this organization.",
                "remediation": "Enable 'Require two-factor authentication' in Organization Settings > Security.",
                "system_logs": {"org": org.login, "mfa_enabled": False}
            }
    except Exception as e:
        logger.error(f"check_org_2fa failed: {e}")
        return {
            "check_id": check_id,
            "title": title,
            "status": "ERROR",
            "severity": "CRITICAL",
            "issue": f"Check failed: {str(e)}",
            "remediation": "Check permissions and retry.",
            "system_logs": {"error": str(e)}
        }

# def check_actions_permissions(repo):
#     """
#     Check if 'Default Workflow Permissions' are Read-Only.
#     Note: This is strictly an Actions setting, usually at Org level or Repo level.
#     The prompt asks for this per repo, but often it's inherited. 
#     PyGithub `repo.get_workflow_permissions()`? No, it might not exist in older PyGithub.
#     We might need to try/except or look for it.
#     If it's missing, we skip or fail safe.
#     """
#     check_id = "actions_permissions"
#     title = "Restrict Default Workflow Permissions"
    
#     try:
#         # Attempt to get actions permissions
#         # Note: repo.get_workflow_permissions() might not be available in all PyGithub versions
#         # fallback to manual request if needed, but let's try standard attribute first if it exists
#         # or just assume specific API endpoint.
        
#         # Valid values: 'read', 'write', 'none'
#         # PASS if 'read' or 'none'. FAIL if 'write'.
        
#         # Using a raw request because PyGithub support varies
#         status, headers, data = repo._requester.requestJson(
#             "GET", 
#             f"{repo.url}/actions/permissions"
#         )
        
#         default_perm = "unknown"
        
#         # Robustly handle response type (Dict or Object)
#         if isinstance(data, dict):
#             default_perm = data.get("default_workflow_permissions", "unknown")
#         elif hasattr(data, "default_workflow_permissions"):
#             default_perm = data.default_workflow_permissions
#         else:
#             # Fallback
#             try:
#                 default_perm = data.default_workflow_permissions
#             except:
#                 pass
        
#         if default_perm in ["read", "none"]:
#              return {
#                 "check_id": check_id,
#                 "title": title,
#                 "status": "PASS",
#                 "severity": "MEDIUM",
#                 "issue": f"Default permissions are restricted ({default_perm}).",
#                 "remediation": "",
#                 "system_logs": {"repo": repo.full_name, "permission": default_perm}
#             }
        
#         if default_perm == "unknown":
#              # Debugging helper
#              keys_found = list(data.keys()) if isinstance(data, dict) else dir(data)
#              return {
#                 "check_id": check_id,
#                 "title": title,
#                 "status": "FAIL",
#                 "severity": "MEDIUM",
#                 "issue": f"Could not determine permissions. Keys found: {keys_found}",
#                 "remediation": "Check token scopes (needs 'workflow' or admin access).",
#                 "system_logs": {"repo": repo.full_name, "data_keys": str(keys_found)}
#             }

#         return {
#             "check_id": check_id,
#             "title": title,
#             "status": "FAIL",
#             "severity": "MEDIUM",
#             "issue": f"Default permissions are too permissive ({default_perm}).",
#             "remediation": "Set Default Workflow Permissions to 'Read repository contents' in Settings > Actions.",
#             "system_logs": {"repo": repo.full_name, "permission": default_perm}
#         }
            
#     except Exception as e:
#         # 404 means Actions might be disabled or no access
#         return {
#             "check_id": check_id,
#             "title": title,
#             "status": "PASS", # Fail safe if we can't check, or "WARN"
#             "severity": "MEDIUM",
#             "issue": "Could not verify permissions (Access Denied or Actions Disabled).",
#             "remediation": "Manually verify Actions permissions.",
#             "system_logs": {"error": str(e)}
#         }



def check_actions_permissions(repo):
    """
    Check if 'Default Workflow Permissions' are Read-Only.
    """
    check_id = "actions_permissions"
    title = "Restrict Default Workflow Permissions"
    
    try:
        # 1. Use the standard PyGithub method (Handles parsing automatically)
        # Requires 'workflow' scope in your token.
        workflow_perms = repo.get_workflow_permissions()
        
        # 2. Extract the permission level
        # The object attribute is 'default_workflow_permissions'
        # Convert to string to be safe (e.g., "read", "write")
        default_perm = str(workflow_perms.default_workflow_permissions)
        
        # 3. Validation Logic
        if default_perm in ["read", "none"]:
             return {
                "check_id": check_id,
                "title": title,
                "status": "PASS",
                "severity": "MEDIUM",
                "issue": f"Default permissions are restricted ({default_perm}).",
                "remediation": "",
                "system_logs": {"repo": repo.full_name, "permission": default_perm}
            }
        else:
            return {
                "check_id": check_id,
                "title": title,
                "status": "FAIL",
                "severity": "MEDIUM",
                "issue": f"Default permissions are too permissive ({default_perm}).",
                "remediation": "Set Default Workflow Permissions to 'Read repository contents' in Settings > Actions.",
                "system_logs": {"repo": repo.full_name, "permission": default_perm}
            }
            
    except Exception as e:
        # If this fails, it is usually because the Token lacks 'workflow' scope
        # or the repo has Actions disabled entirely.
        return {
            "check_id": check_id,
            "title": title,
            "status": "FAIL", 
            "severity": "MEDIUM",
            "issue": "Could not verify permissions (Token Scope Error or Actions Disabled).",
            "remediation": "Ensure Token has 'workflow' scope.",
            "system_logs": {"error": str(e)}
        }

def check_repo_webhooks(repo):
    """
    List active webhooks and flag insecure (HTTP) ones.
    """
    check_id = "repo_webhooks"
    title = "Insecure Webhooks"
    
    try:
        hooks = repo.get_hooks()
        insecure_hooks = []
        
        for hook in hooks:
            if hook.active:
                config = hook.config
                url = config.get("url", "")
                if url.startswith("http://"):
                    insecure_hooks.append(url)
        
        if not insecure_hooks:
            return {
                "check_id": check_id,
                "title": title,
                "status": "PASS",
                "severity": "HIGH",
                "issue": "All webhooks use HTTPS.",
                "remediation": "",
                "system_logs": {"repo": repo.full_name, "hook_count": hooks.totalCount}
            }
        else:
            return {
                "check_id": check_id,
                "title": title,
                "status": "FAIL",
                "severity": "HIGH",
                "issue": f"Found {len(insecure_hooks)} insecure (HTTP) webhooks.",
                "remediation": "Update webhooks to use HTTPS and enable SSL verification.",
                "system_logs": {"repo": repo.full_name, "insecure_urls": insecure_hooks}
            }

    except Exception as e:
        return {
            "check_id": check_id,
            "title": title,
            "status": "ERROR",
            "severity": "HIGH",
            "issue": f"Failed to check webhooks: {e}",
            "remediation": "Check permissions.",
            "system_logs": {"error": str(e)}
        }

def check_branch_reviews(repo):
    """
    Check if Branch Protection requires required_approving_review_count >= 1.
    """
    check_id = "branch_reviews"
    title = "Require Approving Reviews"
    
    try:
        branch = repo.get_branch(repo.default_branch)
        if not branch.protected:
             return {
                "check_id": check_id,
                "title": title,
                "status": "FAIL",
                "severity": "HIGH",
                "issue": "Branch protection is disabled.",
                "remediation": "Enable Branch Protection and require at least 1 review.",
                "system_logs": {"repo": repo.full_name}
            }
            
        protection = branch.get_protection()
        reviews = protection.required_pull_request_reviews
        
        if reviews and reviews.required_approving_review_count >= 1:
            return {
                "check_id": check_id,
                "title": title,
                "status": "PASS",
                "severity": "HIGH",
                "issue": f"Requires {reviews.required_approving_review_count} reviews.",
                "remediation": "",
                "system_logs": {"repo": repo.full_name, "review_count": reviews.required_approving_review_count}
            }
        
        return {
            "check_id": check_id,
            "title": title,
            "status": "FAIL",
            "severity": "HIGH",
            "issue": "Branch protection does not enforce reviews.",
            "remediation": "Enable 'Require a pull request before merging' and set approvals to 1 or more.",
            "system_logs": {"repo": repo.full_name}
        }
        
    except Exception as e:
        # Often fails if protection is absent or permission denied
        return {
            "check_id": check_id,
            "title": title,
            "status": "FAIL",
            "severity": "HIGH",
            "issue": "Reviews NOT enforced (or check failed).",
            "remediation": "Enable Branch Protection and require at least 1 review.",
            "system_logs": {"error": str(e)}
        }
