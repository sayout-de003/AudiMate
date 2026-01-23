from django.db.models import Count
from apps.audits.models import Evidence

class AuditStatsService:
    """
    Shared service for calculating audit statistics.
    Ensures consistency between Executive Dashboard and Excel Exports.
    """
    
    @staticmethod
    def calculate_audit_stats(audit):
        """
        Calculate statistics for a single audit.
        
        Args:
            audit: Audit instance
            
        Returns:
            dict: Dictionary containing stats
        """
        # Fetch all evidence with related question data
        evidence_qs = Evidence.objects.filter(audit=audit).select_related('question')
        
        total_checks = evidence_qs.count()
        passed_checks = evidence_qs.filter(status='PASS').count()
        failed_checks = evidence_qs.filter(status='FAIL').count()
        error_checks = evidence_qs.filter(status='ERROR').count()
        
        # Calculate Compliance Score
        if total_checks > 0:
            compliance_score = (passed_checks / total_checks) * 100
        else:
            compliance_score = 0.0
            
        # Breakdown by Severity for Failures (High Risk Issues)
        # We focus on FAILED items for risk assessment
        severity_counts = evidence_qs.filter(status='FAIL').values('question__severity').annotate(
            count=Count('id')
        )
        
        # Initialize with zeros
        severity_breakdown = {
            'CRITICAL': 0,
            'HIGH': 0,
            'MEDIUM': 0,
            'LOW': 0
        }
        
        for item in severity_counts:
            sev = item.get('question__severity')
            if sev in severity_breakdown:
                severity_breakdown[sev] = item['count']
                
        # Critical Count specifically requested
        critical_count = severity_breakdown['CRITICAL']
        
        return {
            'audit_id': str(audit.id),
            'total_findings': total_checks,
            'passed_count': passed_checks,
            'failed_count': failed_checks,
            'error_count': error_checks,
            'critical_count': critical_count,
            'pass_rate_percentage': round(compliance_score, 1), # Rounded to 1 decimal like Excel
            'severity_breakdown': severity_breakdown
        }
