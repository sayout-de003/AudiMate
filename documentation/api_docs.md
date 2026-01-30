# AuditEase API Documentation

This document provides detailed information about the AuditEase Backend API, including directory structure, authentication, rate limiting, and detailed endpoint definitions.

## 1. Backend Directory Structure

The backend is built using **Django** and **Django Rest Framework (DRF)**.

```
audit_ease/
├── apps/                       # Modular Django Applications
│   ├── audits/                 # Core audit logic, snapshots, evidence
│   ├── billing/                # Stripe integration, subscriptions
│   ├── core/                   # Shared utilities, base models
│   ├── integrations/           # External integrations (GitHub, etc.)
│   ├── notifications/          # Email and system notifications
│   ├── organizations/          # Tenant/Organization management
│   ├── reports/                # PDF/Excel report generation
│   └── users/                  # User authentication and management
├── config/                     # Project configuration
│   ├── settings/               # Environment-based settings (base, local, prod)
│   ├── urls.py                 # Main URL routing
│   └── wsgi.py                 # WSGI entry point
├── middleware/                 # Custom middleware (context, logging)
└── templates/                  # Email and report templates
```

---

## 2. Authentication & Security

### Authentication Methods
The API supports multiple authentication schemes. Most endpoints require authentication.

1.  **JWT Authentication (Preferred)**
    *   **Header**: `Authorization: Bearer <access_token>`
    *   **Obtain Token**: POST `/api/v1/auth/login/`
    *   **Refresh Token**: POST `/api/v1/auth/refresh/`

2.  **Session Authentication** (for browser-based usage)
3.  **Basic Authentication** (for testing/scripts)

### Permissions
*   **IsAuthenticated**: Default for most endpoints.
*   **IsOrgAdmin**: Required for sensitive operations (e.g., managing organization users).
*   **IsSameOrganization**: Ensures users can only access data within their organization.

---

## 3. Rate Limiting

The API implements throttling to prevent abuse.

| Scope | Rate Limit | Description |
| :--- | :--- | :--- |
| **Anonymous** | 100 / day | Unauthenticated requests (e.g., login, register) |
| **User (Global)** | 1000 / hour | Authenticated API requests |
| **Login Failures** | 5 / minute | Brute-force protection |
| **Signups** | 10 / hour | Prevent spam account creation |
| **Audit Creation** | 5 / hour | `AUDIT_RATE_LIMIT` setting |
| **PDF Generation** | 5 / minute | Resource intensive operation |

---

## 4. API Endpoints

### A. Authentication (dj-rest-auth & Users)

#### 1. Core Auth
*   **Login**: `POST /api/v1/auth/login/`
*   **Logout**: `POST /api/v1/auth/logout/`
*   **Refresh Token**: `POST /api/v1/auth/refresh/`
*   **User Details**: `GET /api/v1/auth/user/`
*   **Password Change**: `POST /api/v1/auth/password/change/`
*   **Password Reset**: `POST /api/v1/auth/password/reset/`
*   **Password Reset Confirm**: `POST /api/v1/auth/password/reset/confirm/`

#### 2. Registration & Social
*   **Register**: `POST /api/v1/auth/register/` (Custom)
    *   **Input**: `{ "email": "...", "password": "...", "first_name": "...", "last_name": "..." }`
*   **Registration Verify Email**: `POST /api/v1/auth/registration/verify-email/`
*   **Google Login**: `POST /api/v1/auth/google/`

#### 3. User Profile
*   **Current User**: `GET /api/v1/users/me/`
    *   Returns user details and active organization context.

---

### B. Organizations (Tenancy)

#### 1. Organization Management
*   **List Organizations**: `GET /api/v1/organizations/`
*   **Create Organization**: `POST /api/v1/organizations/`
*   **Retrieve Organization**: `GET /api/v1/organizations/{id}/`
*   **Update Organization**: `PUT/PATCH /api/v1/organizations/{id}/` (Admin only)
*   **Delete Organization**: `DELETE /api/v1/organizations/{id}/` (Admin only)
*   **User Organizations**: `GET /api/v1/user-organizations/` (Simplified list)

#### 2. Member Management
*   **Invite Member**: `POST /api/v1/organizations/{id}/invite_member/`
    *   **Input**: `{ "email": "...", "role": "MEMBER" }`
*   **Accept Invite**: `POST /api/v1/invites/accept/`
*   **Check Invite**: `GET /api/v1/invites/check/`

#### 3. Organization Admin Dashboard
*   **Dashboard Stats**: `GET /api/v1/organizations/{id}/admin/dashboard/`
*   **List Members (Admin)**: `GET /api/v1/organizations/{id}/admin/members/`
*   **Remove Member**: `DELETE /api/v1/organizations/{id}/admin/members/{user_id}/`
*   **Resend Invite**: `POST /api/v1/organizations/{id}/admin/invites/{invite_id}/resend/`
*   **Activity Logs**: `GET /api/v1/organizations/{id}/admin/logs/`
*   **Org Settings**: `GET /api/v1/organizations/{id}/admin/settings/`

---

### C. Audits (Core)

#### 1. Audit Operations
*   **List Audits**: `GET /api/v1/audits/`
*   **Start Audit**: `POST /api/v1/audits/start/` (Rate Limited: 5/hr)
*   **Audit Detail**: `GET /api/v1/audits/{id}/`
*   **Export CSV**: `GET /api/v1/audits/{id}/export/csv/`
*   **Export Excel**: `GET /api/v1/audits/{id}/export/xlsx/`
*   **Export Preview**: `GET /api/v1/audits/{id}/export/preview/`

#### 2. Evidence & Findings
*   **List Evidence**: `GET /api/v1/audits/{id}/evidence/`
*   **Create Evidence**: `POST /api/v1/audits/{id}/evidence/create/`
*   **Upload Evidence**: `POST /api/v1/audits/evidence/upload/`
*   **Milestone**: `POST /api/v1/audits/evidence/milestone/`
*   **Finalize Session**: `POST /api/v1/audits/session/{pk}/finalize/`
*   **Upload Screenshot**: `POST /api/v1/audits/evidence/{pk}/upload_screenshot/`

#### 3. Snapshots (Immutable Records)
*   **List Snapshots**: `GET /api/v1/audits/{id}/snapshots/`
*   **Create Snapshot**: `POST /api/v1/audits/{id}/snapshots/create/`
*   **Snapshot Detail**: `GET /api/v1/audits/snapshots/{pk}/`
*   **Pin Snapshot**: `POST /api/v1/audits/snapshots/{pk}/pin/`
*   **Share Snapshot**: `POST /api/v1/audits/snapshots/{pk}/share/`

#### 4. Dashboard
*   **Summary**: `GET /api/v1/audits/dashboard/summary/`
*   **Stats**: `GET /api/v1/audits/dashboard/stats/`

#### 5. Risk Acceptance
*   **Risk Accept**: `POST /api/v1/audits/risk-accept/`
    *   **Input**: `{ "check_id": "...", "reason": "...", "resource_identifier": "..." }`

#### 6. Public Reports
*   **View Report**: `GET /api/v1/audits/public/reports/{token}/` (No Auth)

---

### D. Integrations

#### 1. Management
*   **List Integrations**: `GET /api/v1/integrations/`
*   **Create Integration**: `POST /api/v1/integrations/`
*   **Retrieve Integration**: `GET /api/v1/integrations/{id}/`
*   **Update Integration**: `PUT/PATCH /api/v1/integrations/{id}/`
*   **Delete Integration**: `DELETE /api/v1/integrations/{id}/`

#### 2. GitHub
*   **Connect**: `GET /api/v1/integrations/github/connect/`
*   **Callback**: `POST /api/v1/integrations/github/callback/`
*   **Webhook**: `POST /api/v1/integrations/webhooks/github/`

---

### E. Billing

#### 1. Operations
*   **Create Checkout Session**: `POST /api/v1/billing/checkout_session/`
    *   **Input**: `{ "organization_id": "...", "price_id": "..." }`
*   **Stripe Webhook**: `POST /api/v1/billing/webhooks/stripe/` (Public)

---

### F. Reports

#### 1. PDF Generation
*   **Generate PDF**: `GET /api/v1/reports/{id}/pdf/` (Rate Limited: 5/min)

---

### G. Sentry Debugging
*   **Trigger Error**: `GET /debug-sentry/` (Staff only)
