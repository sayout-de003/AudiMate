import pytest
from rest_framework import status
from apps.audits.models import Audit, Evidence

@pytest.mark.django_db
def test_audit_lifecycle(admin_client, organization):
    """
    Test the Core Value Loop:
    1. Authenticated Admin starts a new audit.
    2. Admin uploads evidence to the active audit session.
    3. Admin generates a PDF report for the audit.
    """
    
    # 1. Start Audit
    start_url = '/api/v1/audits/start/'
    # Post request to start audit
    response = admin_client.post(start_url)
    
    # Expecting 202 Accepted as it triggers a background task
    assert response.status_code == status.HTTP_202_ACCEPTED
    
    audit_id = response.data['audit_id']
    
    # Verify Audit Created in DB
    audit = Audit.objects.get(id=audit_id)
    assert audit.organization == organization
    assert audit.status == 'PENDING'
    
    # 2. Upload Evidence
    # Endpoint requires session_id, evidence_type, and data
    upload_url = '/api/v1/audits/evidence/upload/'
    evidence_payload = {
        "session_id": audit_id,
        "evidence_type": "log",
        "data": {
            "log_entry": "Critical system access detected", 
            "timestamp": "2024-01-01T12:00:00Z"
        }
    }
    
    response = admin_client.post(upload_url, evidence_payload, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    
    # Verify Evidence Created
    # The view auto-creates a question 'adhoc_upload' if not present
    assert Evidence.objects.filter(audit=audit).exists()
    evidence = Evidence.objects.get(audit=audit)
    assert evidence.raw_data['type'] == 'log'
    
    # 3. Generate PDF
    # This should return the PDF even if audit is running (or might need completion in real app, but requirements say assert 200)
    pdf_url = f'/api/v1/reports/{audit_id}/pdf/'
    response = admin_client.get(pdf_url)
    
    assert response.status_code == status.HTTP_200_OK
    assert response['Content-Type'] == 'application/pdf'
    # Ensure content is not empty
    assert len(response.content) > 0
