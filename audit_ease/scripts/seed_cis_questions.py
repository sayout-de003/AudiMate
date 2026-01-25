
import os
import django

# Setup Django Environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "audit_ease.settings")
django.setup()

from apps.audits.models import Question

# Define new questions
NEW_questions = [
    {
        "key": "cis_1_4_collaborators",
        "title": "CIS 1.4: Restrict Outside Collaborators",
        "description": "Ensure there are no outside collaborators with access to the repository.",
        "severity": "CRITICAL"
    },
    {
        "key": "cis_4_4_force_pushes",
        "title": "CIS 4.4: Prevent Force Pushes",
        "description": "Ensure force pushes are denied on the default branch.",
        "severity": "HIGH"
    },
    {
        "key": "cis_4_5_branch_deletion",
        "title": "CIS 4.5: Prevent Branch Deletion",
        "description": "Ensure deletion of the default branch is blocked.",
        "severity": "HIGH"
    },
    {
        "key": "cis_4_6_status_checks",
        "title": "CIS 4.6: Require Status Checks",
        "description": "Ensure status checks are required to pass before merging.",
        "severity": "MEDIUM"
    },
    {
        "key": "gh_gov_license",
        "title": "GH-GOV-01: License File",
        "description": "Ensure a LICENSE file exists in the repository.",
        "severity": "LOW"
    }
]

def seed_questions():
    print("Seeding new audit questions...")
    count = 0
    for q_data in NEW_questions:
        q, created = Question.objects.get_or_create(
            key=q_data["key"],
            defaults={
                "title": q_data["title"],
                "description": q_data["description"],
                "severity": q_data["severity"]
            }
        )
        if created:
            print(f"[CREATED] {q.title}")
            count += 1
        else:
            print(f"[EXISTS] {q.title}")
            
    print(f"Done. Created {count} new questions.")

seed_questions()
