import sys
from unittest.mock import MagicMock

# 1. Mock dependencies BEFORE import
mock_models = MagicMock()
sys.modules["audit_ease.apps.audits.models"] = mock_models
sys.modules["audit_ease.models"] = mock_models # alias just in case

mock_integrations = MagicMock()
sys.modules["apps.integrations.models"] = mock_integrations
sys.modules["audit_ease.apps.integrations.models"] = mock_integrations

mock_encryption = MagicMock()
sys.modules["services.encryption_manager"] = mock_encryption
sys.modules["audit_ease.services.encryption_manager"] = mock_encryption

mock_aws = MagicMock()
sys.modules["services.aws_service"] = mock_aws
sys.modules["audit_ease.services.aws_service"] = mock_aws

# Also mock celery because shared_task might be imported in other places
sys.modules["celery"] = MagicMock()

# 2. Now import AuditExecutor
# Note: we need to ensure the import path corresponds to PYTHONPATH
# We assume PYTHONPATH=.
try:
    from audit_ease.apps.audits.logic import AuditExecutor
    from audit_ease.services.github_service import GitHubService, GitHubServiceError
except ImportError:
    # Fallback if python path issues
    from apps.audits.logic import AuditExecutor
    from services.github_service import GitHubService

def test_cis_integration_pure():
    print("Testing CIS Integration Wiring (Pure Python Mock)...")
    
    # Setup mocks for logic.py imports
    # logic.py imports Audit, Evidence, Question from .models (which is our mock)
    Audit = mock_models.Audit
    Question = mock_models.Question
    Integration = mock_integrations.Integration
    
    # Mock Audit.objects.get
    mock_audit_instance = MagicMock()
    Audit.objects.get.return_value = mock_audit_instance
    mock_audit_instance.organization.name = "TestOrg"

    # Instantiate Executor
    # It tries to fetch Audit(id) in __init__
    executor = AuditExecutor(audit_id='test-id')
    
    # Mock _get_github_service (helper method) to return our mock service
    mock_service = MagicMock(spec=GitHubService)
    executor._get_github_service = MagicMock(return_value=mock_service)
    
    # Setup Mock Service Data
    mock_service.integration.identifier = "TestOrg"
    mock_service.integration.meta_data = {'repo_name': 'TestOrg/TestRepo'}
    
    # 3. Test check_cis_1_1_mfa
    print("- Testing check_cis_1_1_mfa...")
    mock_service.get_org_details.return_value = {"two_factor_requirement_enabled": True}
    
    status, data, msg = executor.check_cis_1_1_mfa()
    
    if status == 'PASS':
        print("  [PASS] Status OK")
    else:
        print(f"  [FAIL] Status expected PASS got {status}")
        
    if data.get('compliance_standard') == "CIS GitHub Benchmark v1.0":
        print("  [PASS] Compliance Standard OK")
    else:
        print(f"  [FAIL] Missing compliance mapping: {data}")

    # 4. Test check_cis_5_1_codeowners
    print("\n- Testing check_cis_5_1_codeowners...")
    mock_service.get_repo_tree.return_value = [{'path': '.github/CODEOWNERS'}]
    
    status, data, msg = executor.check_cis_5_1_codeowners()
    
    if status == 'PASS':
        print("  [PASS] Status OK")
        print("  Logic wired correctly.")
    else:
        print(f"  [FAIL] Status expected PASS got {status}")

if __name__ == "__main__":
    test_cis_integration_pure()
