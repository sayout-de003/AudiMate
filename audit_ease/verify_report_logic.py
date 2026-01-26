import os
import sys
import json
import django

sys.path.append('/Users/sayantande/audit_full_app')
sys.path.append('/Users/sayantande/audit_full_app/audit_ease')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from apps.audits.models import Evidence, Audit, Question
from apps.organizations.models import Organization
from django.template.loader import render_to_string
from datetime import datetime

def test_report_generation():
    # Setup Data
    org = Organization.objects.first()
    audit = Audit.objects.create(organization=org, status='COMPLETED')
    question, _ = Question.objects.get_or_create(key='test_log_check', defaults={'title': 'Log Check', 'severity': 'HIGH'})
    
    # Evidence with RAW DATA but NO SCREENSHOT
    raw_data = {'error': 'Connection Refused', 'code': 500}
    evidence = Evidence.objects.create(
        audit=audit, 
        question=question, 
        status='FAIL', 
        raw_data=raw_data,
        comment='Log evidence only'
    )
    
    # Mimic views_export.py logic to build context
    check_item = {
        'rule_id': question.key,
        'title': question.title,
        'description': question.description,
        'severity': question.severity,
        'status': 'FAIL',
        'findings': [{
            'resource': 'Test Resource',
            'status': 'FAIL',
            'screenshot': None, # explicitly None
            'raw_data': raw_data,
            'json_log': json.dumps(raw_data, indent=2, default=str),
            'comment': 'Log evidence only'
        }]
    }
    
    context = {
        'audit': audit,
        'stats': {'pass_rate_percentage': 50},
        'checks': [check_item],
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
    }
    
    # Render Template
    html = render_to_string('reports/audit_report.html', context)
    
    # Verify String Presence
    if 'class="json-logs"' in html:
        print("Success: found .json-logs class in HTML")
    else:
        print("Failure: .json-logs class NOT found in HTML")
        
    if 'Connection Refused' in html:
        print("Success: found raw data content in HTML")
    else:
        print("Failure: raw data content NOT found in HTML")

if __name__ == "__main__":
    test_report_generation()
