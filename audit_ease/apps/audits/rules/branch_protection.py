from .base import BaseRule, RuleResult

class BranchProtectionRule(BaseRule):
    """
    Checks if the default branch has protection enabled.
    """
    
    def evaluate(self, data: dict) -> RuleResult:
        # 'data' here is the response from get_branch_protection
        
        if data is None:
            return RuleResult(
                status=False,
                details="No branch protection rules found.",
                compliance_mapping="N/A"
            )

        # Check specific requirements (example: require PR reviews)
        required_reviews = data.get("required_pull_request_reviews", {})
        dismiss_stale = required_reviews.get("dismiss_stale_reviews", False)

        if not dismiss_stale:
             return RuleResult(
                 status=False,
                 details="Stale reviews are not set to dismiss automatically.",
                 compliance_mapping="N/A"
             )

        return RuleResult(
            status=True, 
            details="Branch protection is active and secure.",
            compliance_mapping="N/A"
        )