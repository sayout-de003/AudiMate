from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from .base import BaseRule, RuleResult

CIS_BENCHMARK_V1 = "CIS GitHub Benchmark v1.0"

# --- Group 1: Identity and Access ---

class EnforceMFA(BaseRule):
    """
    CIS 1.1: Ensure multi-factor authentication is required for all members in the organization.
    """
    compliance_standard = CIS_BENCHMARK_V1

    def evaluate(self, data: Dict[str, Any]) -> RuleResult:
        # data source: GET /orgs/{org}
        if not data:
             return RuleResult(False, "No organization data provided.", "CIS 1.1")
        
        mfa_enabled = data.get("two_factor_requirement_enabled", False)
        
        if mfa_enabled:
            return RuleResult(True, "MFA is enforced for the organization.", "CIS 1.1")
        return RuleResult(False, "MFA is NOT enforced for the organization.", "CIS 1.1")


class StaleAdminAccess(BaseRule):
    """
    CIS 1.2: Ensure admins have logged in within the past 90 days.
    """
    compliance_standard = CIS_BENCHMARK_V1

    def evaluate(self, members: list) -> RuleResult:
        # data source: List of members with their last_active date (mocked or from API)
        if not members:
            return RuleResult(False, "No members found to evaluate.", "CIS 1.2")

        stale_admins = []
        now = datetime.now(timezone.utc)
        
        for member in members:
            # Assuming member structure dict with 'role' and 'last_active' (ISO string)
            if member.get("role") == "admin":
                last_active_str = member.get("last_active")
                if last_active_str:
                    try:
                        # Handle basic ISO format, might need robust parsing in prod
                        last_active = datetime.fromisoformat(last_active_str.replace('Z', '+00:00'))
                        if (now - last_active).days > 90:
                            stale_admins.append(member.get("login", "unknown"))
                    except ValueError:
                        # Fallback or log error for invalid date format
                        pass

        if stale_admins:
            return RuleResult(
                False, 
                f"Found stale admins who haven't logged in for 90+ days: {', '.join(stale_admins)}",
                "CIS 1.2"
            )
        
        return RuleResult(True, "No stale admins found.", "CIS 1.2")


class ExcessiveOwners(BaseRule):
    """
    CIS 1.3: Ensure organization has less than 3 owners to prevent 'God Mode' sprawl.
    """
    compliance_standard = CIS_BENCHMARK_V1

    def evaluate(self, members: list) -> RuleResult:
        if not members:
             return RuleResult(False, "No members data provided.", "CIS 1.3")

        admin_count = sum(1 for m in members if m.get("role") == "admin")
        
        if admin_count > 3:
            return RuleResult(
                False, 
                f"Excessive number of owners detected: {admin_count} (Limit: 3).", 
                "CIS 1.3"
            )
        
        return RuleResult(True, f"Owner count is within limits: {admin_count}.", "CIS 1.3")


# --- Group 2: Repository Security ---

class SecretScanningEnabled(BaseRule):
    """
    CIS 2.1: Ensure secret scanning is enabled.
    """
    compliance_standard = CIS_BENCHMARK_V1

    def evaluate(self, repo_data: Dict[str, Any]) -> RuleResult:
        # data source: GET /repos/{owner}/{repo}
        if not repo_data:
            return RuleResult(False, "No repository data provided.", "CIS 2.1")

        sec_analysis = repo_data.get("security_and_analysis", {})
        # security_and_analysis might be None if not enabled/available
        if not sec_analysis:
             return RuleResult(False, "Security and analysis settings are missing or disabled.", "CIS 2.1")

        secret_scanning = sec_analysis.get("secret_scanning", {})
        status = secret_scanning.get("status")

        if status == "enabled":
            return RuleResult(True, "Secret scanning is enabled.", "CIS 2.1")
        
        return RuleResult(False, "Secret scanning is disabled.", "CIS 2.1")


class DependabotEnabled(BaseRule):
    """
    CIS 2.2: Ensure Dependabot security updates are enabled.
    """
    compliance_standard = CIS_BENCHMARK_V1

    def evaluate(self, repo_data: Dict[str, Any]) -> RuleResult:
         if not repo_data:
            return RuleResult(False, "No repository data provided.", "CIS 2.2")

         sec_analysis = repo_data.get("security_and_analysis", {})
         if not sec_analysis:
             return RuleResult(False, "Security and analysis settings are missing or disabled.", "CIS 2.2")
         
         dependabot = sec_analysis.get("dependabot_security_updates", {})
         status = dependabot.get("status")

         if status == "enabled":
             return RuleResult(True, "Dependabot security updates are enabled.", "CIS 2.2")
         
         return RuleResult(False, "Dependabot security updates are disabled.", "CIS 2.2")


class PrivateRepoVisibility(BaseRule):
    """
    CIS 2.5: Ensure repositories tagged as 'Internal' are private.
    """
    compliance_standard = CIS_BENCHMARK_V1

    def evaluate(self, repo_data: Dict[str, Any]) -> RuleResult:
        # This rule logic depends on how 'Internal' tag is determined. 
        # Assuming we check if it is NOT private but conceptually 'internal' (e.g. by topic or just verifying all repos are private)
        # Re-reading requirement: "Fail if private is False AND the repo is tagged as 'Internal'"
        # Assuming 'topics' list contains 'internal' or similar logic.
        
        if not repo_data:
            return RuleResult(False, "No repository data provided.", "CIS 2.5")
            
        topics = repo_data.get("topics", [])
        is_private = repo_data.get("private", False)
        
        # Check if tagged Internal (case-insensitive)
        is_tagged_internal = "internal" in [t.lower() for t in topics]

        if is_tagged_internal and not is_private:
            return RuleResult(False, "Repository is tagged 'Internal' but visibility is Public.", "CIS 2.5")
        
        return RuleResult(True, "Repository visibility compliance passed.", "CIS 2.5")


# --- Group 3: Branch Protection (The "Main" Branch) ---

class EnforceSignedCommits(BaseRule):
    """
    CIS 3.1: Ensure commit signing is required.
    """
    compliance_standard = CIS_BENCHMARK_V1

    def evaluate(self, protection_data: Dict[str, Any]) -> RuleResult:
        # data: GET /repos/{owner}/{repo}/branches/main/protection
        # If protection_data is None/Empty, it means 404/Not Protected.
        if not protection_data:
            return RuleResult(False, "Branch protection is not enabled.", "CIS 3.1")
            
        required_signatures = protection_data.get("required_signatures", {})
        if required_signatures.get("enabled", False):
            return RuleResult(True, "Signed commits are required.", "CIS 3.1")
            
        return RuleResult(False, "Signed commits are NOT required.", "CIS 3.1")


class BranchProtectionMain(BaseRule):
    """
    CIS 4.1: Ensure the default branch is protected.
    """
    compliance_standard = CIS_BENCHMARK_V1

    def evaluate(self, protection_data: Dict[str, Any]) -> RuleResult:
        # The mere existence of valid protection_data implies 200 OK. 
        # If it was 404, the caller should pass None or empty dict.
        
        if protection_data:
            return RuleResult(True, "Main branch is protected.", "CIS 4.1")
        
        return RuleResult(False, "Main branch is NOT protected.", "CIS 4.1")


class RequireCodeReviews(BaseRule):
    """
    CIS 4.2: Ensure at least one approving review is required.
    """
    compliance_standard = CIS_BENCHMARK_V1

    def evaluate(self, protection_data: Dict[str, Any]) -> RuleResult:
        if not protection_data:
            return RuleResult(False, "Branch protection is not enabled.", "CIS 4.2")

        pr_reviews = protection_data.get("required_pull_request_reviews", {})
        # If the key is missing, reviews might not be required at all
        if not pr_reviews:
             return RuleResult(False, "Pull request reviews are not required.", "CIS 4.2")

        count = pr_reviews.get("required_approving_review_count", 0)
        
        if count >= 1:
            return RuleResult(True, f"Requires {count} approving reviews.", "CIS 4.2")
            
        return RuleResult(False, "Does not require min 1 approving review.", "CIS 4.2")


class DismissStaleReviews(BaseRule):
    """
    CIS 4.3: Ensure stale reviews are dismissed when new commits are pushed.
    """
    compliance_standard = CIS_BENCHMARK_V1

    def evaluate(self, protection_data: Dict[str, Any]) -> RuleResult:
        if not protection_data:
            return RuleResult(False, "Branch protection is not enabled.", "CIS 4.3")

        pr_reviews = protection_data.get("required_pull_request_reviews", {})
        dismiss_stale = pr_reviews.get("dismiss_stale_reviews", False)
        
        if dismiss_stale:
            return RuleResult(True, "Stale reviews are dismissed automatically.", "CIS 4.3")
            
        return RuleResult(False, "Stale reviews are NOT dismissed automatically.", "CIS 4.3")


class RequireLinearHistory(BaseRule):
    """
    CIS 4.5: Ensure linear history is required (no merge commits).
    """
    compliance_standard = CIS_BENCHMARK_V1

    def evaluate(self, protection_data: Dict[str, Any]) -> RuleResult:
        if not protection_data:
             return RuleResult(False, "Branch protection is not enabled.", "CIS 4.5")
             
        linear_history = protection_data.get("required_linear_history", {})
        if linear_history.get("enabled", False):
            return RuleResult(True, "Linear history is required.", "CIS 4.5")
            
        return RuleResult(False, "Linear history is NOT required.", "CIS 4.5")


# --- Group 4: Governance ---

class CodeOwnersExist(BaseRule):
    """
    CIS 5.1: Ensure CODEOWNERS file exists.
    """
    compliance_standard = CIS_BENCHMARK_V1

    def evaluate(self, repo_tree: list) -> RuleResult:
        # input: List of file paths or tree structure from git/api
        # Assuming input is a list of strings (filenames) for simplicity, 
        # or a list of dicts with 'path' key.
        
        found = False
        valid_paths = [".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"]
        
        # Check if data is list of dicts (GitHub API style) or list of strings
        paths = []
        if isinstance(repo_tree, list):
            if repo_tree and isinstance(repo_tree[0], dict):
                paths = [item.get("path") for item in repo_tree]
            elif repo_tree and isinstance(repo_tree[0], str):
                paths = repo_tree
        
        for p in valid_paths:
            if p in paths:
                found = True
                break
                
        if found:
            return RuleResult(True, "CODEOWNERS file found.", "CIS 5.1")
            
        return RuleResult(False, "CODEOWNERS file missing.", "CIS 5.1")
