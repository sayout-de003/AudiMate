from django.utils import timezone
from apps.audits.models import Audit, Evidence
from apps.integrations.models import Integration
from apps.audits.rules.branch_protection import BranchProtectionRule
from services.github_service import GitHubService

# Registry mapping Question types to Rule classes
RULE_REGISTRY = {
    "BRANCH_PROTECTION": BranchProtectionRule,
    # "ACCESS_CONTROL": AccessControlRule,
}

class AuditOrchestrator:
    def __init__(self, audit_id: int):
        self.audit = Audit.objects.get(id=audit_id)
        self.integration = self.audit.organization.integrations.first() # Simplified
        self.github_service = GitHubService(self.integration)

    def run_audit(self):
        """
        Main entry point to run all checks for this audit.
        """
        self.audit.status = "RUNNING"
        self.audit.save()

        try:
            # 1. Fetch Data (The "Context")
            # In a real app, you might fetch different data for different rules.
            # For this example, we check the 'main' branch of a specific repo.
            target_repo = "my-org/my-repo" # Ideally comes from Audit configuration
            protection_data = self.github_service.get_branch_protection(target_repo)

            # 2. Iterate through Questions defined in the Audit
            for question in self.audit.questions.all():
                rule_class = RULE_REGISTRY.get(question.rule_key)
                
                if not rule_class:
                    continue

                # 3. Execute Rule
                rule_engine = rule_class()
                passed, details = rule_engine.evaluate(protection_data)

                # 4. Save Evidence
                Evidence.objects.create(
                    audit=self.audit,
                    question=question,
                    is_compliant=passed,
                    raw_data=details,
                    checked_at=timezone.now()
                )

            self.audit.status = "COMPLETED"
            
        except Exception as e:
            self.audit.status = "FAILED"
            self.audit.error_log = str(e)
        
        finally:
            self.audit.save()