from django.db import models
from apps.audits.models import Audit

class Report(models.Model):
    audit = models.OneToOneField(
        Audit,
        on_delete=models.CASCADE,
        related_name='report',
        help_text="The audit for which this report was generated"
    )
    file = models.FileField(upload_to='reports/', help_text="The generated PDF file")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report for Audit {self.audit.id}"
