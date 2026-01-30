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

# Snapshot Services
import hashlib
import json
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from apps.audits.models import AuditSnapshot

def create_audit_snapshot(audit_id: str, user, name: str = None) -> 'AuditSnapshot':
    """
    Creates an immutable snapshot of an audit.
    
    Args:
        audit_id: The ID of the audit to snapshot
        user: The user triggering the snapshot
        name: Optional user-friendly name for the snapshot
    
    Returns:
        The created AuditSnapshot instance
    """
    audit = Audit.objects.select_related('organization', 'triggered_by').get(id=audit_id)
    evidence_qs = Evidence.objects.filter(audit=audit).select_related('question').order_by('created_at')
    
    # 1. Serialize the full state
    # We construct a dictionary that represents the full state of the audit + evidence
    
    evidence_data = []
    for ev in evidence_qs:
        evidence_data.append({
            'question_key': ev.question.key,
            'question_title': ev.question.title,
            'question_severity': ev.question.severity,
            'status': ev.status,
            'raw_data': ev.raw_data,
            'comment': ev.comment,
            'created_at': ev.created_at.isoformat(),
        })
        
    snapshot_data = {
        'audit': {
            'id': str(audit.id),
            'organization_id': str(audit.organization.id),
            'organization_name': audit.organization.name,
            'triggered_by_email': audit.triggered_by.email if audit.triggered_by else None,
            'status': audit.status,
            'created_at': audit.created_at.isoformat(),
            'completed_at': audit.completed_at.isoformat() if audit.completed_at else None,
        },
        'evidence': evidence_data,
        'metadata': {
            'snapshot_created_at':  timezone.now().isoformat(),
            'total_evidence_count': len(evidence_data),
        }
    }
    
    # Calculate checksum of the data to ensure integrity
    # Convert to stable JSON string for hashing
    json_str = json.dumps(snapshot_data, sort_keys=True, cls=DjangoJSONEncoder)
    checksum = hashlib.sha256(json_str.encode('utf-8')).hexdigest()
    
    # Determine version number
    current_version = AuditSnapshot.objects.filter(audit=audit).aggregate(models.Max('version'))['version__max'] or 0
    new_version = current_version + 1
    
    # Default name if not provided
    if not name:
        name = f"Snapshot v{new_version}"
        
    snapshot = AuditSnapshot.objects.create(
        audit=audit,
        organization=audit.organization,
        name=name,
        version=new_version,
        data=snapshot_data,
        checksum=checksum,
        created_by=user
    )
    
    # FREEZE/LOCK the audit
    audit.status = 'FROZEN'
    audit.save(update_fields=['status'])
    
    return snapshot