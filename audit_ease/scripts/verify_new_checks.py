
import unittest
from unittest.mock import MagicMock
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from apps.audits.rules.new_checks import (
    check_org_2fa, 
    check_actions_permissions, 
    check_repo_webhooks, 
    check_branch_reviews
)

class TestNewChecks(unittest.TestCase):
    def test_check_org_2fa_pass(self):
        org = MagicMock()
        org.two_factor_requirement_enabled = True
        org.login = "test-org"
        
        result = check_org_2fa(org)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['check_id'], 'org_2fa')

    def test_check_org_2fa_fail(self):
        org = MagicMock()
        org.two_factor_requirement_enabled = False
        org.login = "test-org"
        
        result = check_org_2fa(org)
        self.assertEqual(result['status'], 'FAIL')

    def test_check_actions_permissions_pass(self):
        repo = MagicMock()
        repo.url = "https://api.github.com/repos/org/repo"
        repo.full_name = "org/repo"
        # Mock requestJson response
        repo._requester.requestJson.return_value = (200, {}, {"default_workflow_permissions": "read"})
        
        result = check_actions_permissions(repo)
        self.assertEqual(result['status'], 'PASS')
        self.assertIn("restricted", result['issue'])

    def test_check_actions_permissions_fail(self):
        repo = MagicMock()
        repo.url = "https://api.github.com/repos/org/repo"
        repo.full_name = "org/repo"
        repo._requester.requestJson.return_value = (200, {}, {"default_workflow_permissions": "write"})
        
        result = check_actions_permissions(repo)
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn("too permissive", result['issue'])

    def test_check_repo_webhooks_pass(self):
        repo = MagicMock()
        hook1 = MagicMock(active=True, config={"url": "https://example.com"})
        hook2 = MagicMock(active=False, config={"url": "http://insecure.com"}) # Inactive shouldn't trigger
        repo.get_hooks.return_value = MagicMock(totalCount=2, __iter__=lambda x: iter([hook1, hook2]))
        
        result = check_repo_webhooks(repo)
        self.assertEqual(result['status'], 'PASS')

    def test_check_repo_webhooks_fail(self):
        repo = MagicMock()
        hook1 = MagicMock(active=True, config={"url": "http://insecure.com"})
        repo.get_hooks.return_value = [hook1]
        
        result = check_repo_webhooks(repo)
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn("insecure", result['issue'])

    def test_check_branch_reviews_pass(self):
        repo = MagicMock()
        repo.default_branch = "main"
        branch = MagicMock(protected=True)
        protection = MagicMock()
        protection.required_pull_request_reviews.required_approving_review_count = 1
        branch.get_protection.return_value = protection
        repo.get_branch.return_value = branch
        
        result = check_branch_reviews(repo)
        self.assertEqual(result['status'], 'PASS')

    def test_check_branch_reviews_fail_count(self):
        repo = MagicMock()
        repo.default_branch = "main"
        branch = MagicMock(protected=True)
        protection = MagicMock()
        protection.required_pull_request_reviews.required_approving_review_count = 0
        branch.get_protection.return_value = protection
        repo.get_branch.return_value = branch
        
        result = check_branch_reviews(repo)
        self.assertEqual(result['status'], 'FAIL')

if __name__ == '__main__':
    unittest.main()
