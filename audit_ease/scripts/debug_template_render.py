
import os
import sys
import django
from django.conf import settings
from django.template.loader import render_to_string
from datetime import datetime

# Setup Django standalone
sys.path.append('/Users/sayantande/audit_full_app/audit_ease')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

def debug_render():
    print("DEBUG: Starting template render debug...")
    
    # Mock Objects
    class MockOrg:
        name = "Test Organization"
        
    class MockAudit:
        id = "550e8400-e29b-41d4-a716-446655440000"
        organization = MockOrg()
        created_at = datetime.now()
        
    stats = {
        'pass_rate_percentage': 85.5,
        'total_findings': 10,
        'passed_count': 8,
        'failed_count': 2
    }
    
    checks = [
        {
            'rule_id': 'BR_01',
            'title': 'Test Rule',
            'description': 'Test Description',
            'severity': 'HIGH',
            'status': 'FAIL',
            'passed_count': 0,
            'findings': [
                {
                    'resource': 'repo-1',
                    'status': 'FAIL',
                    'check': {'severity': 'HIGH'}, # Emulating nested access if needed
                    'comment': 'Test Comment',
                    'remediation': 'Fix it now',
                    'json_log': '{"error": "bad"}',
                    'screenshot': None
                }
            ]
        }
    ]

    context = {
        'audit': MockAudit(),
        'stats': stats,
        'checks': checks,
        'generated_at': "2023-01-01 12:00"
    }
    
    # Render
    try:
        html = render_to_string('reports/audit_report_fixed.html', context)
        print("DEBUG: Render successful.")
        
        # Check for unrendered tags
        unrendered = []
        tags_to_check = ["{{ audit.organization.name }}", "{{ check.severity }}", "{{ finding.remediation }}"]
        
        for tag in tags_to_check:
            if tag in html:
                unrendered.append(tag)
                
        if unrendered:
            print(f"FAIL: Unrendered tags found: {unrendered}")
            # print snippet
            idx = html.find(unrendered[0])
            print(f"Snippet: {html[idx-50:idx+50]}")
        else:
            print("SUCCESS: No unrendered tags found.")
            
        # Verify specific values
        if "Test Organization" in html:
            print("SUCCESS: 'Test Organization' found.")
        else:
            print("FAIL: 'Test Organization' NOT found.")
            
    except Exception as e:
        print(f"ERROR: Rendering failed: {e}")

if __name__ == "__main__":
    debug_render()
