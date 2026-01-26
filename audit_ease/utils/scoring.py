def calculate_audit_score(audit_instance):
    """
    Calculates the audit score based on a weighted subtraction model.
    
    Algorithm:
    Base: Start with 100.
    Deductions: Iterate through failed checks:
        CRITICAL: -15 points
        HIGH: -10 points
        MEDIUM: -5 points
        LOW: -0 points.
    Floor: max(calculated_score, 0)
    
    Args:
        audit_instance: The Audit model instance to calculate score for.
        
    Returns:
        int: The calculated score (0-100).
    """
    
    # Base score
    score = 100
    
    # Deductions mapping
    deductions = {
        'CRITICAL': 15,
        'HIGH': 10,
        'MEDIUM': 5,
        'LOW': 0
    }
    
    # Iterate through failed evidence
    # We assume 'FAIL' is the status for failure. 
    # Adjust if your system uses different status codes for failure.
    failed_evidence = audit_instance.evidence.filter(status='FAIL')
    
    for evidence in failed_evidence:
        severity = evidence.question.severity
        deduction_points = deductions.get(severity, 0)
        score -= deduction_points
        
    # Apply floor
    return max(score, 0)
