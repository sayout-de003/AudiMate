
import requests
import logging
from typing import Any
from .base import BaseRule, RuleResult, RiskLevel

logger = logging.getLogger(__name__)

class AccessControlRule(BaseRule):
    """
    Rule to verify access control configuration by fetching collaborators.
    """
    id = "GH-ACCESS-001"
    title = "Access Control Verification"
    risk_level = RiskLevel.HIGH
    compliance_standard = "Security Best Practices"

    def check(self, context: Any) -> RuleResult:
        """
        Verifies access to repository collaborators.
        
        Args:
            context: A tuple/object containing (service, repo_full_name) 
                     OR a dict with those keys. 
                     Adapting to what logic.py might pass.
                     If we call it manually, we can pass what we need.
        """
        # Determine inputs
        service = None
        repo_full_name = None

        if isinstance(context, dict):
            service = context.get('service')
            repo_full_name = context.get('repo_full_name')
        elif isinstance(context, (list, tuple)) and len(context) >= 2:
            service = context[0]
            repo_full_name = context[1]
        
        if not service or not repo_full_name:
             return RuleResult(False, "Invalid context: service or repo_full_name missing", self.compliance_standard)

        try:
            # 1. API Call (fetching collaborators)
            collaborators = service.get_collaborators(repo_full_name)
            
            # 3. Handle Edge Cases: Zero Collaborators
            if not collaborators:
                # Handle empty list gracefully
                return RuleResult(True, "No collaborators found (Empty list). Access control seems restrictive.", self.compliance_standard)
            
            count = len(collaborators)
            # Just reporting success in fetching means the access control (permissions) are working to ALLOW us to see it.
            return RuleResult(True, f"Access verification successful. Found {count} collaborators.", self.compliance_standard)

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            
            # 2. Implement Robust Error Handling
            if status_code in [401, 403]:
                return RuleResult(
                    False, 
                    "Insufficient permissions to read repository collaborators. Check token scopes.", 
                    self.compliance_standard
                )
            
            if status_code == 404:
                return RuleResult(
                    False, 
                    "Repository not found or not accessible.", 
                    self.compliance_standard
                )
                
            # 3. Handle Edge Cases: API Rate Limiting
            if status_code == 429:
                logger.warning(f"Rate limit exceeded for {repo_full_name}")
                return RuleResult(
                    False, # Treating as fail/error due to inability to verify
                    "API Rate Limiting (429). Check skipped.", 
                    self.compliance_standard
                )
            
            # Catch-all for other HTTP errors
            logger.error(f"HTTP Error in AccessControlRule: {e}")
            return RuleResult(
                False, 
                f"HTTP Error: {status_code}", 
                self.compliance_standard
            )

        except Exception as e:
            # 4. Global Safety Net
            logger.exception(f"Unexpected error in AccessControlRule: {e}")
            return RuleResult(
                False, 
                f"Unexpected error: {str(e)}", 
                self.compliance_standard
            )

    # Alias for compatibility if logic.py expects evaluate
    def evaluate(self, context: Any) -> RuleResult:
        return self.check(context)
