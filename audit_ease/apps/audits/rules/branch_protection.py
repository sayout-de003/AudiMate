from .base import AuditRule

class BranchProtectionRule(AuditRule):
    """
    Checks if the default branch has protection enabled.
    """
    
    def evaluate(self, data: dict) -> tuple[bool, dict]:
        # 'data' here is the response from get_branch_protection
        
        if data is None:
            return False, {"reason": "No branch protection rules found."}

        # Check specific requirements (example: require PR reviews)
        required_reviews = data.get("required_pull_request_reviews", {})
        dismiss_stale = required_reviews.get("dismiss_stale_reviews", False)

        if not dismiss_stale:
             return False, {
                 "reason": "Stale reviews are not set to dismiss automatically.",
                 "raw_data": required_reviews
             }

        return True, {"message": "Branch protection is active and secure."}