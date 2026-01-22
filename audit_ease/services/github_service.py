import requests
import logging
from typing import Optional, Dict, Any
from apps.integrations.models import Integration

logger = logging.getLogger(__name__)

class GitHubServiceError(Exception):
    """Base exception for GitHub service errors."""
    pass

class GitHubAuthenticationError(GitHubServiceError):
    """Raised when GitHub authentication fails."""
    pass

class GitHubService:
    """
    Production-ready GitHub API client with security checks and error handling.
    
    This service replaces the mock/random audit checks with real GitHub API calls.
    Every method performs actual compliance checks against GitHub organizations.
    """
    BASE_URL = "https://api.github.com"
    TIMEOUT = 10  # seconds

    def __init__(self, integration: Integration):
        """
        Initialize the service.
        
        The 'magic' happens here: 
        accessing `integration.access_token` automatically decrypts the 
        stored bytes into a string we can use in headers.
        """
        self.integration = integration
        
        # Guard clause: Ensure we actually have a token to work with
        token = integration.access_token
        if not token:
            raise GitHubAuthenticationError(f"Integration {integration.id} is missing an access token.")

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AuditEase-SecurityAudit/1.0"
        })
        
        # Verify authentication works early
        self._verify_authentication()

    def _verify_authentication(self) -> None:
        """Verify that the token is valid by making a test call."""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/user",
                timeout=self.TIMEOUT
            )
            if response.status_code == 401:
                raise GitHubAuthenticationError("Invalid or expired GitHub token")
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub authentication verification failed: {e}")
            raise GitHubAuthenticationError(f"Failed to verify GitHub token: {e}")

    def get_org_members(self, org: str) -> list:
        """
        Fetches all members of a GitHub organization.
        Used to verify membership and RBAC setup.
        """
        url = f"{self.BASE_URL}/orgs/{org}/members"
        
        try:
            response = self.session.get(url, timeout=self.TIMEOUT)
            if response.status_code == 404:
                logger.warning(f"Organization {org} not found or access denied")
                return []
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch members for {org}: {e}")
            raise GitHubServiceError(f"Failed to fetch org members: {e}")

    def check_org_two_factor_enforced(self, org: str) -> Dict[str, Any]:
        """
        Check if 2FA is enforced for an organization.
        CRITICAL SECURITY CHECK: Verifies the actual organization setting two_factor_requirement_enabled.
        
        Returns:
            {
                'status': 'PASS' | 'FAIL',
                'severity': 'CRITICAL' | 'HIGH',
                'two_factor_enabled': bool,
                'message': str,
                'data': {...}
            }
        """
        url = f"{self.BASE_URL}/orgs/{org}"
        
        try:
            response = self.session.get(url, timeout=self.TIMEOUT)
            
            if response.status_code == 404:
                logger.warning(f"Organization {org} not found or access denied")
                return {
                    "status": "FAIL",
                    "severity": "CRITICAL",
                    "two_factor_enabled": False,
                    "message": f"Organization '{org}' not found or access denied",
                    "data": {"org": org, "error": "org_not_found"}
                }
            
            if response.status_code == 403:
                logger.warning(f"Insufficient permissions to check 2FA for {org}")
                return {
                    "status": "FAIL",
                    "severity": "CRITICAL",
                    "two_factor_enabled": False,
                    "message": f"Permission Denied - Grant read:org scope to verify organization settings",
                    "data": {"org": org, "error": "permission_denied", "required_scope": "read:org"}
                }
            
            response.raise_for_status()
            org_data = response.json()
            
            # Check the two_factor_requirement_enabled attribute
            two_factor_enabled = org_data.get('two_factor_requirement_enabled', False)
            
            status = 'PASS' if two_factor_enabled else 'FAIL'
            severity = 'INFO' if two_factor_enabled else 'CRITICAL'
            
            return {
                "status": status,
                "severity": severity,
                "two_factor_enabled": two_factor_enabled,
                "message": (
                    f"Organization '{org}' 2FA requirement: "
                    f"{'ENABLED' if two_factor_enabled else 'DISABLED'}"
                ),
                "data": {
                    "org": org,
                    "two_factor_requirement_enabled": two_factor_enabled,
                    "org_login": org_data.get('login', org),
                    "org_type": org_data.get('type', 'N/A')
                }
            }
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error checking 2FA for {org}: {e}")
            if e.response.status_code == 403:
                return {
                    "status": "FAIL",
                    "severity": "CRITICAL",
                    "two_factor_enabled": False,
                    "message": f"Permission Denied - Grant read:org scope to verify organization settings",
                    "data": {"org": org, "error": "permission_denied", "required_scope": "read:org"}
                }
            return {
                "status": "ERROR",
                "severity": "HIGH",
                "two_factor_enabled": False,
                "message": f"Failed to check 2FA status: HTTP {e.response.status_code}",
                "data": {"org": org, "error": f"http_{e.response.status_code}"}
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch 2FA status for {org}: {e}")
            return {
                "status": "ERROR",
                "severity": "HIGH",
                "two_factor_enabled": False,
                "message": f"Failed to verify 2FA setting: {type(e).__name__}",
                "data": {"org": org, "error": type(e).__name__}
            }

    def get_repo_details(self, repo_full_name: str) -> dict:
        """
        Fetches basic repository metadata.
        Example repo_full_name: 'audit_ease/backend'
        """
        url = f"{self.BASE_URL}/repos/{repo_full_name}"
        
        try:
            response = self.session.get(url, timeout=self.TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"Failed to fetch repo {repo_full_name}: {e}")
            raise GitHubServiceError(f"Failed to fetch repo details: {e}")

    def get_branch_protection(self, repo_full_name: str, branch: str = "main") -> Optional[dict]:
        """
        Fetches branch protection rules for a repository branch.
        Returns None if no protection exists (404), raises error for other failures.
        
        COMPLIANCE CHECK: Verifies required branch protections are in place.
        """
        url = f"{self.BASE_URL}/repos/{repo_full_name}/branches/{branch}/protection"
        
        try:
            response = self.session.get(url, timeout=self.TIMEOUT)
            
            # 404 is a valid state (No rules configured), not an application error
            if response.status_code == 404:
                return None
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching protection for {repo_full_name}/{branch}: {e}")
            raise GitHubServiceError(f"Failed to fetch branch protection: {e}")

    def check_branch_protection_rules(self, repo_full_name: str, branch: str = "main") -> Dict[str, Any]:
        """
        Comprehensive branch protection compliance check.
        Verifies critical security practices are enforced.
        """
        protection = self.get_branch_protection(repo_full_name, branch)
        
        if protection is None:
            return {
                "status": "FAIL",
                "severity": "CRITICAL",
                "message": f"No branch protection rules configured for {repo_full_name}/{branch}",
                "data": {
                    "repo": repo_full_name,
                    "branch": branch,
                    "protection_enabled": False
                }
            }
        
        # Check critical requirements
        checks = {
            "dismiss_stale_reviews": protection.get("dismiss_stale_pull_request_approvals", False),
            "require_code_review": protection.get("require_pull_request_reviews", {}).get("required_approving_review_count", 0) > 0,
            "enforce_admins": protection.get("enforce_admins", False),
            "require_status_checks": protection.get("required_status_checks", {}).get("strict", False),
        }
        
        all_passed = all(checks.values())
        
        return {
            "status": "PASS" if all_passed else "FAIL",
            "severity": "HIGH" if not all_passed else "INFO",
            "message": f"Branch protection for {repo_full_name}/{branch}: {'Compliant' if all_passed else 'Missing checks'}",
            "data": {
                "repo": repo_full_name,
                "branch": branch,
                "protection_enabled": True,
                "checks": checks,
                "failed_checks": [k for k, v in checks.items() if not v]
            }
        }

    def get_repo_secret_scanning(self, repo_full_name: str) -> Dict[str, Any]:
        """
        Check if secret scanning is enabled on a repository.
        CRITICAL: Prevents accidental credential exposure.
        """
        url = f"{self.BASE_URL}/repos/{repo_full_name}"
        
        try:
            response = self.session.get(url, timeout=self.TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            secret_scanning_enabled = data.get("secret_scanning", False)
            
            return {
                "status": "PASS" if secret_scanning_enabled else "FAIL",
                "severity": "HIGH",
                "message": f"Secret scanning is {'enabled' if secret_scanning_enabled else 'disabled'}",
                "data": {
                    "repo": repo_full_name,
                    "secret_scanning_enabled": secret_scanning_enabled
                }
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking secret scanning for {repo_full_name}: {e}")
            raise GitHubServiceError(f"Failed to check secret scanning: {e}")

    def get_org_details(self, org: str) -> Dict[str, Any]:
        """
        Fetches detailed organization metadata.
        """
        url = f"{self.BASE_URL}/orgs/{org}"
        
        try:
            response = self.session.get(url, timeout=self.TIMEOUT)
            if response.status_code == 404:
                return {}
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch org details for {org}: {e}")
            raise GitHubServiceError(f"Failed to fetch org details: {e}")

    def get_repo_file_contents(self, repo_full_name: str, path: str) -> Optional[Dict[str, Any]]:
        """
        Fetches file contents or metadata. Used to check if a file exists.
        Returns None if file does not exist (404).
        """
        url = f"{self.BASE_URL}/repos/{repo_full_name}/contents/{path}"
        try:
            response = self.session.get(url, timeout=self.TIMEOUT)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # If it's a 404 not caught above (e.g. from raise_for_status if needed, but handled)
            logger.error(f"Failed to fetch file {path} for {repo_full_name}: {e}")
            raise GitHubServiceError(f"Failed to fetch file contents: {e}")

    def get_repo_tree(self, repo_full_name: str, branch: str = "main", recursive: bool = True) -> list:
        """
        Fetches thegit tree for a repo. Useful for finding files like CODEOWNERS in multiple locations.
        """
        url = f"{self.BASE_URL}/repos/{repo_full_name}/git/trees/{branch}?recursive={'1' if recursive else '0'}"
        try:
            response = self.session.get(url, timeout=self.TIMEOUT)
            if response.status_code == 404:
                 # Branch might not exist or empty repo
                 return []
            response.raise_for_status()
            data = response.json()
            return data.get('tree', [])
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch tree for {repo_full_name}: {e}")
            # Non-critical, return empty list to result in Fail for existence checks
            return []



# import requests
# from django.conf import settings
# from apps.integrations.models import Integration

# class GitHubService:
#     BASE_URL = "https://api.github.com"

#     def __init__(self, integration: Integration):
#         """
#         Initialize with an Integration instance to access the encrypted token.
#         """
#         self.integration = integration
#         # decrypt_token() is a hypothetical method on your Integration model
#         self.token = integration.decrypt_token() 
#         self.headers = {
#             "Authorization": f"Bearer {self.token}",
#             "Accept": "application/vnd.github.v3+json",
#         }

#     def get_repo_details(self, repo_full_name: str) -> dict:
#         """
#         Fetches basic repository metadata.
#         Example repo_full_name: 'audit_ease/backend'
#         """
#         url = f"{self.BASE_URL}/repos/{repo_full_name}"
#         response = requests.get(url, headers=self.headers)
        
#         if response.status_code != 200:
#             # In production, use custom exceptions here
#             response.raise_for_status()
            
#         return response.json()

#     def get_branch_protection(self, repo_full_name: str, branch: str = "main") -> dict:
#         """
#         Fetches branch protection rules. 
#         Note: Returns 404 if no protection exists, which is valid data, not strictly an error.
#         """
#         url = f"{self.BASE_URL}/repos/{repo_full_name}/branches/{branch}/protection"
#         response = requests.get(url, headers=self.headers)
        
#         if response.status_code == 404:
#             return None # No protection rules exist
            
#         if response.status_code != 200:
#             response.raise_for_status()

#         return response.json()