# AuditEase - Enterprise Security Audit Platform

## 1. Project Overview

**AuditEase** is a B2B SaaS platform designed to automate security compliance audits for organizations. It allows companies to run automated checks against their infrastructure (GitHub, AWS, etc.), view failure details, and track compliance over time. The platform supports multi-tenancy with strict data isolation, role-based access control (RBAC), and a subscription-based billing model via Stripe.

### Key Features
*   **Multi-Tenancy**: Complete data isolation between organizations.
*   **Automated Audits**: Background workers run compliance checks asynchronously.
*   **RBAC**: Granular permissions (Admin, Member, Viewer).
*   **Billing**: Subscription management with Stripe (Checkout & Webhooks).
*   **Security**: Encrypted storage for integration tokens (Fernet).

---

## 2. Tech Stack

### Backend Core
*   **Language**: Python 3.10+
*   **Framework**: Django 6.0
*   **API**: Django Rest Framework (DRF)
*   **Authentication**: SimpleJWT (JWT) + Session Auth via `django.contrib.auth`

### Data & Storage
*   **Database**: PostgreSQL (Production) / SQLite (Development)
*   **Cache/Queue**: Redis
*   **Async Tasks**: Celery
*   **Encryption**: `cryptography` (Fernet) for sensitive token storage

### Infrastructure & Tools
*   **Containerization**: Docker
*   **Payments**: Stripe API
*   **Documentation**: Markdown

---

## 3. Folder Structure

The project follows a modular Django app structure within `audit_ease/`.

```
audit_ease/
├── apps/                   # key application modules
│   ├── audits/             # Core business logic (Audit, Evidence)
│   ├── billing/            # Stripe integration
│   ├── integrations/       # External tool connections (GitHub, AWS)
│   ├── organizations/      # Tenant & Membership management
│   ├── users/              # Authentication & User model
│   ├── notifications/      # Email & Alerting service
│   └── reports/            # PDF/CSV Export logic
├── config/                 # Project-wide settings & URL routing
│   ├── settings/           # Split settings (base, local, production)
│   └── urls.py             # Main URL entry point
├── middleware/             # Custom middleware (OrgContext, AuditLog)
├── templates/              # Email templates
├── manage.py               # Django entry point
└── requirements.txt        # Python dependencies
```

---

## 4. Module-wise Documentation

### 4.1 Users Module (`apps.users`)
Handles user authentication and profile management.
*   **Key Model**: `User`
    *   Uses **Email** as the unique identifier (Username is removed).
    *   **ID**: UUID for security.
*   **Key Features**:
    *   Registration & Login (JWT).
    *   `get_organization()` helper to resolve current tenant context.

### 4.2 Organizations Module (`apps.organizations`)
Manages multi-tenancy and access control.
*   **Key Models**:
    *   `Organization`: The tenant unit. Contains Stripe customer/subscription IDs.
    *   `Membership`: Links User to Organization with a Role (`ADMIN`, `MEMBER`, `VIEWER`).
    *   `OrganizationInvite`: Manages secure invitation tokens (7-day expiry).
*   **Permissions**:
    *   `IsSameOrganization`: Ensures users only access their own data.
    *   `IsOrgAdmin`: Restricts sensitive actions (e.g., invites, billing) to Admins.

### 4.3 Audits Module (`apps.audits`)
The core engine of the platform.
*   **Key Models**:
    *   `Audit`: Represents a single run. Statuses: `PENDING` -> `RUNNING` -> `COMPLETED`/`FAILED`.
    *   `Evidence`: Individual findings linked to `Question` (the check definition). Status: `PASS`/`FAIL`.
*   **Architecture**:
    *   **Async Execution**: Audits run in background threads/Celery tasks to prevent request blocking.
    *   **Rate Limiting**: Limits audit initiation per user (default 5/hour).
    *   **Streaming Export**: Efficient CSV generation for large datasets.

### 4.4 Billing Module (`apps.billing`)
Handles monetization.
*   **Integration**: Stripe via `stripe-python`.
*   **Flow**:
    1.  User clicks "Upgrade".
    2.  `checkout_session` creates a Stripe Session.
    3.  User pays on Stripe.
    4.  Stripe sends `checkout.session.completed` webhook.
    5.  `stripe_webhook` handler updates Organization subscription status to `active`.

### 4.5 Integrations Module (`apps.integrations`)
Manages connections to third-party tools.
*   **Security**: Uses **Fernet Symmetric Encryption** to store Access/Refresh tokens in the database.
*   **Key Model**: `Integration` (stores `_access_token` as binary blob).

---

## 5. API Documentation

All API endpoints are prefixed with `/api/v1/`.
**Authentication**: Required for all endpoints (except `auth/` and `webhooks/`). passing `Authorization: Bearer <token>`.

### Authentication & Users
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/auth/register/` | Register a new user account. |
| `POST` | `/auth/login/` | Obtain JWT Access/Refresh tokens. |
| `GET` | `/users/me/` | Get current user profile and active organization context. |

### Organizations
| Method | Endpoint | Description | Perms |
| :--- | :--- | :--- | :--- |
| `GET` | `/organizations/` | List organizations user belongs to. | Member |
| `POST` | `/organizations/` | Create a new organization (User becomes Admin). | Auth |
| `POST` | `/organizations/{id}/invite_member/` | Invite email to organization. | **Admin** |
| `DELETE` | `/organizations/{id}/members/{user_id}/` | Remove a member. | **Admin** |
| `POST` | `/invites/accept/` | Accept an invitation (requires token). | Auth |

### Audits (Core)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/audits/start/` | Trigger a new audit run (Async). |
| `GET` | `/audits/` | List all audits for current org. |
| `GET` | `/audits/{id}/` | Get audit status and details. |
| `GET` | `/audits/{id}/evidence/` | Get full list of findings/evidence. |
| `GET` | `/audits/dashboard/summary/` | Get aggregated stats (Pass %, Issues by Severity). |

### Billing
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/billing/checkout-session/` | Create a Stripe Checkout URL. |
| `POST` | `/billing/webhooks/stripe/` | (Public) Stripe Webhook listener. |

---

## 6. Setup & Installation

### Prerequisites
*   Python 3.10+
*   Redis (for Celery/Caching)
*   PostgreSQL (Recommended) or SQLite

### 6.1 Environment Variables
Create a `.env` file in `audit_ease/` (copy from `.env.example`).

```bash
# General
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=super-secret-key-change-me
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=sqlite:///db.sqlite3

# Security (Required for Integrations)
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FERNET_KEY=your-fernet-key-here

# Stripe (Billing)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
FRONTEND_URL=http://localhost:3000

# Rate Limits
AUDIT_RATE_LIMIT=10/h
```

### 6.2 Local Development
1.  **Clone & Install Dependencies**:
    ```bash
    git clone <repo-url>
    cd audit_ease
    pip install -r requirements.txt
    ```

2.  **Apply Migrations**:
    ```bash
    python manage.py migrate
    ```

3.  **Run Development Server**:
    ```bash
    python manage.py runserver
    ```

4.  **Run Celery Worker** (in separate terminal):
    ```bash
    celery -A config worker --loglevel=info
    ```

### 6.3 Production Deployment
1.  **Set Environment**: Ensure `DJANGO_DEBUG=False` and all keys are set.
2.  **Encryption Check**: Run `./production_env_setup.sh` to verify secure keys.
3.  **Docker Deployment**:
    ```bash
    docker-compose -f docker-compose.prod.yml up -d --build
    ```
4.  **Static Files**:
    ```bash
    python manage.py collectstatic --noinput
    ```

---

## 7. Security Architecture

### Data Isolation
We use **Logical Isolation** at the application layer.
*   Every critical query is filtered by `organization=request.user.organization`.
*   Middleware (`OrgContextMiddleware`) attempts to resolve the organization for every request.
*   The `IsSameOrganization` permission class rejects any attempt to access resources ID belonging to another tenant.

### Token Security
Integration tokens (e.g., GitHub Access Tokens) are **Never** stored in plain text.
*   **Encryption**: `apps.integrations.models.Integration` uses `_access_token` (BinaryField).
*   **Mechanism**: On save, data is encrypted via `Fernet`. On access, it is decrypted dynamically.
*   **Key Management**: The `FERNET_KEY` env var is the singular secret master key. **Do not lose this** or all tokens become unrecoverable.

---

## 8. Testing

Run the full test suite using Django's test runner:

```bash
python manage.py test apps/
```

To run tests for a specific module:
```bash
python manage.py test apps.audits
```
