from django.db import models
from django.conf import settings
import uuid
import os
from datetime import datetime

def evidence_upload_path(instance, filename):
    # audit_{audit_id}_rule_{rule_code}_{timestamp}.png
    ext = filename.split('.')[-1]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    new_filename = f"audit_{instance.audit.id}_rule_{instance.question.key}_{timestamp}.{ext}"
    # Use formatted date directories to keep things organized
    date_path = datetime.now().strftime('%Y/%m')
    return os.path.join(f'audit_proofs/{date_path}/', new_filename)

class Question(models.Model):
    SEVERITY_CHOICES = [
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    ]

    key = models.CharField(max_length=50, unique=True, help_text="Unique identifier like 'github_2fa'")
    title = models.CharField(max_length=255)
    description = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='MEDIUM')
    
    def __str__(self):
        return f"[{self.severity}] {self.title}"

class Audit(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('FROZEN', 'Frozen'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='audits',
        help_text="The organization this audit belongs to. Critical for data isolation.",
        null=False,
        blank=False,
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audits_triggered',
        help_text="The user who initiated this audit"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RUNNING')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(default=0, help_text="Audit compliance score (0-100)")
    score_value = models.IntegerField(default=0, help_text="Audit compliance score value")

    class Meta:
        # Ensure organization isolation: Company A's audits can't be accessed by Company B
        indexes = [
            models.Index(fields=['organization', 'created_at']),
            models.Index(fields=['organization', 'status']),
        ]
        # Order by organization first to support efficient querying
        ordering = ['-organization_id', '-created_at']

    def __str__(self):
        return f"Audit {self.id} [{self.organization.name}] - {self.status}"

class Evidence(models.Model):
    STATUS_CHOICES = [
        ('PASS', 'Pass'),
        ('FAIL', 'Fail'),
        ('ERROR', 'Error'),
        ('RISK_ACCEPTED', 'Risk Accepted'),
    ]

    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name='evidence')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    raw_data = models.JSONField(
        default=dict,
        help_text="Raw API response or logs proving the result. Contains actual evidence from external systems."
    )
    comment = models.TextField(
        blank=True,
        null=True,
        help_text="Human-readable summary of the finding"
    )
    STATUS_STATE_CHOICES = [
        ('OPEN', 'Open'),
        ('FIXED', 'Fixed'),
        ('RISK_ACCEPTED', 'Risk Accepted'),
    ]

    # NEW FIELDS FOR INDUSTRY STANDARD PROOFS
    screenshot = models.ImageField(upload_to=evidence_upload_path, null=True, blank=True)
    remediation_steps = models.TextField(null=True, blank=True)
    remediation_status = models.CharField(max_length=20, default='OPEN') # Deprecated, use status_state
    status_state = models.CharField(max_length=20, choices=STATUS_STATE_CHOICES, default='OPEN')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # unique_together = ('audit', 'question')  # Removed to allow multiple repos per question
        # Optimize queries for audit result retrieval
        indexes = [
            models.Index(fields=['audit', 'status']),
            models.Index(fields=['question', 'status']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Evidence {self.question.key} [{self.status}] for Audit {self.audit.id}"

class AuditSnapshot(models.Model):
    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        related_name='snapshots',
        help_text="The source audit this snapshot was created from"
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        help_text="Organization isolation"
    )
    name = models.CharField(max_length=255, help_text="User-friendly name for this snapshot")
    version = models.PositiveIntegerField(help_text="Incremental version number for this audit")
    data = models.JSONField(help_text="The immutable snapshot data (audit + evidence)")
    checksum = models.CharField(max_length=64, help_text="SHA256 checksum of the data field for integrity")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        help_text="User who triggered the snapshot"
    )
    is_pinned = models.BooleanField(default=False, help_text="If True, this snapshot cannot be deleted by retention policies")
    pdf_file = models.FileField(upload_to='audit_reports/', null=True, blank=True, help_text="Generated PDF report for this snapshot")

    class Meta:
        unique_together = ('audit', 'version')
        ordering = ['-version']
        indexes = [
            models.Index(fields=['organization', 'created_at']),
        ]

    def __str__(self):
        return f"Snapshot {self.version}: {self.name} ({self.audit.id})"
class ScanHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, help_text="User associated with this scan metric")
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='scan_history',
        help_text="Organization for this history record",
        null=True, 
        blank=True
    )
    date = models.DateTimeField(auto_now_add=True)
    score = models.IntegerField(help_text="Daily Posture Score (0-100)")
    total_fail = models.IntegerField()
    total_pass = models.IntegerField()

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['organization', 'date']),
        ]

    def __str__(self):
        return f"History {self.date.date()} - Score: {self.score}"

class RiskAcceptanceException(models.Model):
    check_id = models.CharField(max_length=50, help_text="The key of the check to skip/waive (e.g. cis_1_1)")
    reason = models.TextField(help_text="Justification for why this risk is accepted")
    date_accepted = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        help_text="User who accepted the risk"
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='risk_exceptions',
        help_text="Organization this exception applies to"
    )
    resource_identifier = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        help_text="Specific resource to waive (e.g. repo name). If empty, waives for entire org?"
    )

    class Meta:
        unique_together = ('organization', 'check_id', 'resource_identifier')

    def __str__(self):
        return f"Exception for {self.check_id} on {self.resource_identifier or 'Global'} ({self.organization})"

class PublicLink(models.Model):
    token = models.CharField(
        primary_key=True, 
        max_length=64, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Secure random token for public access"
    )
    snapshot = models.ForeignKey(
        AuditSnapshot, 
        on_delete=models.CASCADE,
        related_name='public_links',
        help_text="The snapshot exposed by this link"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    views_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    def __str__(self):
        return f"Public Link {self.token[:8]}... for {self.snapshot}"
