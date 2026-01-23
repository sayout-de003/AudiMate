import logging
from github import Github, GithubException
from django.conf import settings
from allauth.socialaccount.models import SocialToken

logger = logging.getLogger(__name__)

class GitHubScanner:
    """
    Scanner for performing audit checks on a specific GitHub repository.
    Uses PyGithub for API interactions.
    """

    def __init__(self, user, repo_name):
        """
        Initialize the scanner with a user and repository name.
        
        Args:
            user: The user triggering the scan (used to fetch OAuth token).
            repo_name: Full name of the repository (e.g., "owner/repo").
        """
        self.user = user
        self.repo_name = repo_name
        self.github = self._get_github_client()
        self.repo = self._get_repo()

    def _get_github_client(self):
        """
        Initialize authenticated PyGithub client using the user's SocialToken.
        """
        try:
            # Fetch the GitHub token for the user
            social_token = SocialToken.objects.get(
                account__user=self.user, 
                account__provider='github'
            )
            return Github(social_token.token)
        except SocialToken.DoesNotExist:
            logger.error(f"No GitHub token found for user {self.user.id}")
            raise ValueError("User must have a connected GitHub account to perform scans.")

    def _get_repo(self):
        """
        Fetch the Repository object from GitHub.
        """
        try:
            return self.github.get_repo(self.repo_name)
        except GithubException as e:
            logger.error(f"Failed to fetch repo {self.repo_name}: {e}")
            raise ValueError(f"Repository {self.repo_name} not found or access denied.")

    def run_check(self):
        """
        Execute the audit checks.
        
        Returns:
            dict: Audit results including metadata and check status.
        """
        results = {
            "repo_size": self.repo.size,
            "is_private": self.repo.private,
            "has_readme": False,
            "details": {}
        }

        # Check for README
        try:
            # Try getting README.md
            self.repo.get_contents("README.md")
            results["has_readme"] = True
        except GithubException as e:
            if e.status == 404:
                # README not found
                 results["has_readme"] = False
            else:
                # Other error, log it but assume false for safety or re-raise
                logger.warning(f"Error checking README for {self.repo_name}: {e}")
                results["details"]["readme_error"] = str(e)
        
        return results
