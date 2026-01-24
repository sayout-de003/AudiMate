try:
    from audit_ease.apps.audits.rules.cis_benchmark import (
        EnforceMFA, StaleAdminAccess, ExcessiveOwners,
        SecretScanningEnabled, DependabotEnabled, PrivateRepoVisibility,
        EnforceSignedCommits, BranchProtectionMain, RequireCodeReviews, 
        DismissStaleReviews, RequireLinearHistory,
        CodeOwnersExist
    )
    from audit_ease.apps.audits.rules.base import BaseRule, RuleResult
    
    print("Imports successful.")
    
    # Quick instantiation test
    rules = [
        EnforceMFA(), StaleAdminAccess(), ExcessiveOwners(),
        SecretScanningEnabled(), DependabotEnabled(), PrivateRepoVisibility(),
        EnforceSignedCommits(), BranchProtectionMain(), RequireCodeReviews(),
        DismissStaleReviews(), RequireLinearHistory(),
        CodeOwnersExist()
    ]
    
    print(f"Successfully instantiated {len(rules)} rules.")
    
    # Quick type check
    assert isinstance(rules[0], BaseRule)
    print("Inheritance check passed.")

except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
