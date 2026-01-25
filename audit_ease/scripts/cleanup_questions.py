
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "audit_ease.settings")
django.setup()

from apps.audits.models import Question

def cleanup_and_seed():
    print("Cleaning up old/test questions...")
    # Delete test questions
    deleted_test, _ = Question.objects.filter(key__startswith="q_").delete()
    print(f"Deleted {deleted_test} test questions.")
    
    # Delete old duplicate keys if any (based on title or key pattern)
    # The user lists 'cis_1_1_private', 'cis_1_2_branch_protection'.
    # My logic.py maps 'cis_1_1_mfa', 'cis_1_2_stale_admins', etc.
    # So 'cis_1_1_private' is definitely WRONG/Old.
    # I should align the DB with logic.py.
    
    # List of valid keys from logic.py
    VALID_KEYS = [
        'github_2fa', 'github_branch_protection', 'github_secret_scanning', 'github_org_members',
        's3_public_access', 'aws_root_mfa', 'cloudtrail_enabled', 'db_encryption', 'unused_iam_users', 
        'security_groups_22', 'https_enforced', 'admin_mfa',
        'cis_1_1_mfa', 'cis_1_2_stale_admins', 'cis_1_3_excessive_owners',
        'cis_2_1_secret_scanning', 'cis_2_2_dependabot', 'cis_2_5_private_repo',
        'cis_3_1_signed_commits', 'cis_4_1_branch_protection', 'cis_4_2_code_reviews',
        'cis_4_3_dismiss_stale', 'cis_4_5_linear_history', 'cis_5_1_codeowners',
        'access_control',
        'cis_1_4_collaborators', 'cis_4_4_force_pushes', 'cis_4_5_branch_deletion',
        'cis_4_6_status_checks', 'gh_gov_license',
        # Keep 'readme_exists' as it seems valid in fixture
        'readme_exists'
    ]
    
    # Delete anything NOT in VALID_KEYS
    all_qs = Question.objects.all()
    count_deleted = 0
    for q in all_qs:
        if q.key not in VALID_KEYS:
            print(f"Deleting invalid key: {q.key} ({q.title})")
            q.delete()
            count_deleted += 1
            
    print(f"Deleted {count_deleted} invalid questions.")
    
    # Re-seed from fixtures (simulated)
    # I will just run 'python manage.py loaddata fixtures/questions.json' after this script.

cleanup_and_seed()
