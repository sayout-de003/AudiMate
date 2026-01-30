# Coding Standards & Guidelines

## 1. Python & Django Style Guide

We strictly follow **PEP 8** standards.

### Tools
*   **Formatter**: `Black` (line length: 88).
*   **Linter**: `Ruff` or `Flake8`.
*   **Import Sorting**: `isort` (profile: black).

### Naming Conventions
*   **Variables/Functions**: `snake_case` (e.g., `calculate_audit_score`, `user_profile`).
*   **Classes/Exceptions**: `CapWords` (e.g., `AuditSnapshot`, `InvalidTokenError`).
*   **Constants**: `UPPER_CASE` (e.g., `MAX_RETRY_ATTEMPTS`).
*   **Private Members**: `_leading_underscore` (e.g., `_internal_helper`).

### Django Best Practices
*   **Fat Models, Thin Views**: Put business logic in Models or Services, not in Views.
*   **Explicit is better than Implicit**: Use `Question.objects.filter(...)` instead of magic lookups.
*   **Use Services**: Complex logic involving multiple models or external APIs should go into `services/`.
    *   ✅ `services.audit_service.run_scan(audit)`
    *   ❌ implementing scan logic inside `AuditViewSet.create()`

## 2. API Response Guidelines

All API endpoints must return standardized JSON responses.

### Success
```json
{
  "status": "success",
  "data": { ... }
}
```

### Error
```json
{
  "status": "error",
  "code": "permission_denied",
  "message": "You do not have permission to perform this action.",
  "details": { ... }
}
```

## 3. Git Workflow

### Commit Messages
Follow the **Conventional Commits** specification:
*   `feat: add new audit snapshot capability`
*   `fix: resolve 403 error on export endpoint`
*   `docs: update API documentation`
*   `refactor: move billing logic to service layer`

### Branching Strategy
*   `main`: Production-ready code.
*   `develop`: Integration branch (optional).
*   `feature/foo-bar`: New features.
*   `bugfix/issue-123`: Bug fixes.

## 4. Linting Configuration (Example)

**pyproject.toml (Black)**
```toml
[tool.black]
line-length = 88
target-version = ['py312']
```

**ruff.toml**
```toml
select = ["E", "F", "I", "W"]
ignore = ["E501"] # Let Black handle line lengths
```
