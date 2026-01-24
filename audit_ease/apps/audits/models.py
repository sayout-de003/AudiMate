from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
import uuid

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
    ]

    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name='evidence')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    raw_data = models.JSONField(
        default=dict,
        help_text="Raw API response or logs proving the result. Contains actual evidence from external systems."
    )
    comment = models.TextField(
        blank=True,
        null=True,
        help_text="Human-readable summary of the finding"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('audit', 'question')
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

    class Meta:
        unique_together = ('audit', 'version')
        ordering = ['-version']
        indexes = [
            models.Index(fields=['organization', 'created_at']),
        ]

    def __str__(self):
        return f"Snapshot {self.version}: {self.name} ({self.audit.id})"