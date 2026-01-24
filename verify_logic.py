import os
import django
from unittest.mock import MagicMock, patch

import sys
from unittest.mock import MagicMock
sys.modules["celery"] = MagicMock()

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'audit_ease.config.settings.base')
django.setup()

from audit_ease.apps.audits.logic import AuditExecutor
from audit_ease.apps.audits.models import Question, Audit
from audit_ease.services.github_service import GitHubService

def test_cis_integration():
    print("Testing CIS Integration Wiring...")
    
    # 1. Mock Audit and Question
    mock_audit = MagicMock(spec=Audit)
    mock_audit.organization.name.return_value = "TestOrg"
    
    # Create mock questions for CIS rules
    cis_keys = [
        'cis_1_1_mfa', 'cis_1_2_stale_admins', 'cis_5_1_codeowners'
    ]
    
    # 2. Mock GitHubService
    with patch('audit_ease.apps.audits.logic.Integration.objects.get') as mock_int_get, \
         patch('audit_ease.apps.audits.logic.GitHubService') as MockService, \
         patch('audit_ease.apps.audits.logic.Audit.objects.get', return_value=mock_audit):
         
        # Setup Service Mock
        service_instance = MockService.return_value
        service_instance.integration.identifier = "TestOrg"
        service_instance.integration.meta_data = {'repo_name': 'TestOrg/TestRepo'}
        
        # Mock responses for data fetchers
        service_instance.get_org_details.return_value = {"two_factor_requirement_enabled": True}
        service_instance.get_org_members.return_value = []
        service_instance.get_repo_tree.return_value = [{'path': 'CODEOWNERS'}]
        
        executor = AuditExecutor(audit_id='dummy-uuid')
        
        # 3. Test individual check methods
        print("- Testing check_cis_1_1_mfa...")
        status, data, msg = executor.check_cis_1_1_mfa()
        assert status == 'PASS', f"Expected PASS, got {status}"
        assert data['compliance_standard'] == "CIS GitHub Benchmark v1.0"
        print("  OK")

        print("- Testing check_cis_5_1_codeowners...")
        status, data, msg = executor.check_cis_5_1_codeowners()
        assert status == 'PASS', f"Expected PASS, got {status}"
        print("  OK")
        
        print("\nIntegration wiring verified successfully!")

if __name__ == "__main__":
    test_cis_integration()
