# Backend Technical Design Document (TDD)

## 1. Top-Level Folder Structure

The project follows a "cookiecutter-django" style structure, optimized for modularity and scalability.

```text
audit_ease/
├── apps/                   # Django Apps (Business Logic)
│   ├── audits/             # Audit engine, snapshots, evidence models
│   ├── billing/            # Stripe integration, subscriptions
│   ├── organizations/      # Multi-tenancy, RBAC, Invites
│   ├── users/              # Custom User model, authentication
│   └── reports/            # PDF generation, aggregate reporting
├── config/                 # Project Configuration
│   ├── settings/           # Split settings (base, local, production)
│   ├── urls.py             # Main URL routing
│   └── wsgi/asgi.py        # Entry points
├── services/               # Cross-cutting business logic (Service Layer)
├── requirements/           # Dependency management
└── manage.py               # Django CLI entry point
```

## 2. App & Module Responsibilities

### `apps.organizations`
*   **Responsibility**: Core multi-tenancy engine.
*   **Models**: `Organization`, `Membership`, `OrganizationInvite`.
*   **Key Design**: Uses UUIDs for isolation. Implements RBAC logic.

### `apps.audits`
*   **Responsibility**: The heart of the product. Manages security scans.
*   **Models**: `Audit`, `Question` (Rules), `Evidence`, `AuditSnapshot`.
*   **Key Design**:
    *   `Audit` links to `Organization` for isolation.
    *   `AuditSnapshot` provides immutable history (frozen time-series data).

### `apps.billing`
*   **Responsibility**: Monetization.
*   **Integrations**: Stripe (Checkout Sessions, Webhooks).
*   **Key Logic**: Syncs Stripe subscription status to `Organization.subscription_status`.

### `apps.users`
*   **Responsibility**: Identity management.
*   **Models**: Custom `User` model inheriting from `AbstractUser`.

## 3. Design Patterns

### Service Layer Pattern
**Location**: `services/`
**Purpose**: Decouple complex business logic from Views/Models.
**Examples**:
*   `services/github_service.py`: Encapsulates all GitHub API interactions.
*   `services/aws_service.py`: Handles AWS interactions (S3, etc.).
*   `services/export_service.py`: Logic for generating CSV/PDF reports.

### Signal Dispatcher Pattern
**Location**: `apps/*/signals.py`
**Purpose**: Decouple unrelated components via event-driven actions.
**Examples**:
*   When `Organization` is created -> Trigger default `Team` creation.
*   When `Stripe Webhook` received -> Update `Organization` status.

### Serializer Pattern (DRF)
**Location**: `apps/*/serializers.py`
**Purpose**: Handle complex data validation and transformation.
**Rules**:
*   Validation logic belongs in `validate()`.
*   Representation logic belongs in `to_representation()`.

## 4. API Design Principles

*   **RESTful**: Resources are nouns (`/audits/`, `/organizations/`).
*   **Versioning**: URL-based versioning (`/api/v1/...`).
*   **Authentication**: Bearer Token (JWT).
*   **Response Format**: standardized JSON.
    ```json
    {
      "count": 10,
      "next": "http://...",
      "previous": null,
      "results": [...]
    }
    ```
*   **Pagination**: LimitOffsetPagination or PageNumberPagination for list endpoints.

## 5. Error Handling Strategy

*   **Global Exception Handling**: DRF's default exception handler is extended to return standard error structures.
*   **Status Codes**:
    *   `400 Bad Request`: Validation errors.
    *   `401 Unauthorized`: Invalid/Missing token.
    *   `403 Forbidden`: Permission denied (RBAC / Subscription).
    *   `404 Not Found`: Resource doesn't exist.
    *   `429 Too Many Requests`: Rate limit exceeded.
    *   `500 Internal Server Error`: Unexpected crashes (logged to Sentry).

## 6. Authentication & Authorization

### Authentication
*   **Library**: `djangorestframework-simplejwt`
*   **Flow**:
    1.  `POST /api/v1/auth/login/` -> Returns `access` and `refresh` tokens.
    2.  Client sends `Authorization: Bearer <access>` header.

### Authorization
*   **Library**: DRF Permissions (`rest_framework.permissions`)
*   **Custom Permissions**:
    *   `IsSameOrganization`: Ensures cross-tenant data isolation.
    *   `IsOrgAdmin`: Restricts sensitive actions to admins.
    *   `HasActiveSubscription`: Gates premium features.

## 7. Rate Limiting

*   **Library**: `django-ratelimit` or DRF Throttling.
*   **Policy**:
    *   **Anon**: 5/min (Prevent brute force on login).
    *   **User**: 100/min (General API usage).
    *   **Scans**: Limiting expensive audit scans (e.g., 5 per hour per org) to prevent DOS.
