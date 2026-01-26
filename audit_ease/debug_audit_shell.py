from apps.audits.models import Audit, Evidence

audit_id = "e1421898-264c-46c5-8265-3f6e87c13b2f"

try:
    audit = Audit.objects.get(id=audit_id)
    print(f"Audit Found: {audit}")
    
    evidence_count = Evidence.objects.filter(audit=audit).count()
    print(f"Evidence Count: {evidence_count}")
    
    if evidence_count > 0:
        print("First 5 Evidence items:")
        for ev in Evidence.objects.filter(audit=audit)[:5]:
            print(f"- {ev.question.key}: {ev.status}")
    else:
        print("❌ NO EVIDENCE FOUND for this audit.")

except Audit.DoesNotExist:
    print(f"❌ Audit {audit_id} not found.")
except Exception as e:
    print(f"Error: {e}")
