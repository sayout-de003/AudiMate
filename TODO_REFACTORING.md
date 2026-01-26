# TODO: Django Audit System Refactoring

## Task 1: Fix Duplicate Tests (apps/audits/logic.py)
- [x] Add LEGACY_QUESTION_KEYS constant
- [x] Modify execute_checks to exclude legacy keys

## Task 2: Fix Data Visibility & Add Preview (apps/audits/views_export.py)
- [x] Add preview mode with ?preview=true query parameter
- [x] Improve data processing for resource_name and remediation_display
- [x] Return HTML response for preview, PDF for download

## Task 3: Fix Template (templates/reports/pro_audit_report.html)
- [x] Add default filter for resource_name
- [x] Ensure all check details are visible in PDF

## Testing
- [ ] Verify tests run only once per audit
- [ ] Verify PDF shows all checks with details
- [ ] Verify preview endpoint works
---
## Summary of Changes

### 1. apps/audits/logic.py
- Added `LEGACY_QUESTION_KEYS` constant with legacy keys to exclude
- Modified `execute_checks()` to use `.exclude(key__in=LEGACY_QUESTION_KEYS)`
- This prevents duplicate test execution

### 2. apps/audits/views_export.py (AuditExportPDFView)
- Added preview mode: `?preview=true` returns HTML, default returns PDF
- Improved resource_name extraction from `raw_source` sub-dictionary
- Improved remediation_display to use `question.remediation` or `question.description` when comment is empty
- Removed deduplication to show ALL checks
- Added proper sorting by status (FAIL first) then severity

### 3. templates/reports/pro_audit_report.html
- Updated Resource column to use `{{ finding.resource_name|default:"Global" }}`
- Template already has proper Evidence and Remediation columns with error display


