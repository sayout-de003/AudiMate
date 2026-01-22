# AuditEase - Technical Documentation

> **Source of Truth** | **Version 1.0**

Welcome to the official technical documentation for **AuditEase**. This document provides a comprehensive deep dive into the architecture, workflows, code logic, and deployment strategies for the platform. It is designed for developers, architects, and DevOps engineers.

---

## 1. 🏗️ High-Level Architecture & Directory Structure

### 1.1 Architecture Pattern
**AuditEase** follows a **Monolithic Architecture** built on **Django**. However, it adopts a **Modular Monolith** approach, where business logic is strictly encapsulated within distinct "apps" (modules) rather than being scattered.

*   **Why Monolithic?**
    *   **Simplicity:** Easier to develop, test, and deploy for a core team.
    *   **Data Integrity:** ACID transactions across modules (e.g., creating an Organization and its first Member) are trivial.
    *   **Latency:** No network overhead between internal services (e.g., Audits calling Organizations).
*   **Why Modular?**
    *   Allows future extraction of modules (e.g., `audits` worker) into microservices if scaling requires it.
    *   Enforces clear boundaries via "Service Layers".

**Design Principles:**
*   **Django REST Framework (DRF):** The entire frontend communication happens via REST APIs.
*   **Async Execution:** Long-running tasks (Audits) are offloaded to **Celery + Redis** to keep the API responsive.
*   **Multi-Tenancy:** "Logical Separation" is enforced at the application layer. Every critical query filters by `organization_id`.

### 1.2 System Architecture Diagram
```mermaid
graph TD
    Client[Web Client / User] -->|HTTPS/JSON| LoadBalancer[Load Balancer / Nginx]
    LoadBalancer -->|Reverse Proxy| Django[Django App Server]
    
    subgraph "Application Cluster"
        Django -->|Task Queue| Redis[Redis Cache & Broker]
        Django -->|SQL| DB[(PostgreSQL Master)]
        
        CeleryWorker[Celery Worker Nodes] -->|Consume Tasks| Redis
        CeleryWorker -->|Update Status| DB
    end
    
    subgraph "External Services"
        Django -->|Checkout/Webhooks| Stripe[Stripe Payments]
        CeleryWorker -->|API Checks| GitHub[GitHub API]
        CeleryWorker -->|API Checks| AWS[AWS API]
    end
```

### 1.3 Directory Tree & Responsibility
The project is structured to separate configuration from application logic.

```bash
audit_ease/
├── apps/                       # 📦 CORE MODULES
│   ├── audits/                 # Audit engine, compliance rules, evidence logic
│   ├── billing/                # Stripe integration, subscription management
│   ├── integrations/           # Third-party token storage (GitHub, AWS)
│   ├── organizations/          # Tenant management, Memberships, RBAC
│   ├── users/                  # Custom User model, Auth logic
│   ├── notifications/          # Email services (SendGrid/SMTP)
│   └── reports/                # PDF generation logic
├── config/                     # ⚙️ PROJECT CONFIG
│   ├── settings/               # Environment-specific settings (base, local, prod)
│   ├── urls.py                 # Main URL routing
│   └── wsgi.py                 # WSGI entry point
├── middleware/                 # 🛡️ MIDDLEWARE
│   ├── org_context.py          # Injects 'request.organization'
│   └── audit_logging.py        # Logs sensitive actions
├── scripts/                    # 🛠️ UTILITIES
│   └── rotate_fernet_keys.py   # Key rotation script
├── services/                   # 🧠 SHARED BUSINESS LOGIC
│   └── encryption_manager.py   # Encryption helpers
└── manage.py                   # Django definition entry point
```

---

## 2. 🔄 Workflows & Logic Flows

### 2.1 User Registration & Organization Setup
**Use Case:** A new user signs up and creates their first organization.
**Key Logic:**
1.  User registers (`/auth/register/`).
2.  User creates an Organization (`/organizations/`).
3.  System automatically assigns the Creator as **ADMIN**.
4.  User is now "logged in" to this Context.

```mermaid
sequenceDiagram
    actor U as User
    participant API as Django API
    participant DB as Database

    U->>API: POST /auth/register/ (email, password)
    API->>DB: Create User
    DB-->>API: User Created
    API-->>U: 201 Created (Token)

    U->>API: POST /organizations/ (name="Acme Inc")
    API->>DB: Create Organization
    API->>DB: Create Membership (User, Org, Role=ADMIN)
    DB-->>API: Success
    API-->>U: 201 Created (Org ID)
```

### 2.2 Audit Execution Flow (Async)
**Use Case:** User clicks "Run Audit". The system must not freeze while checking 100+ resources.
**Key Logic:**
1.  API creates an `Audit` record (Status: `PENDING`).
2.  API spawns a **Background Thread/Task**.
3.  API returns `202 Accepted` immediately.
4.  Worker runs checks, creates `Evidence`, and updates `Audit` status.

```mermaid
sequenceDiagram
    actor U as User
    participant API as Django API
    participant Worker as Background Worker
    participant DB as Database
    participant Ext as GitHub API

    U->>API: POST /audits/start/
    API->>DB: Create Audit (PENDING)
    API->>Worker: Dispatch Task (audit_id)
    API-->>U: 202 Accepted (audit_id)

    par Async Execution
        Worker->>DB: Set Status = RUNNING
        Worker->>Ext: Fetch Repo Config
        Ext-->>Worker: JSON Data
        Worker->>Worker: Evaluate Rules (Pass/Fail)
        Worker->>DB: Save Evidence
        Worker->>DB: Set Status = COMPLETED
    end

    loop Polling
        U->>API: GET /audits/{id}/
        API->>DB: Check Status
        DB-->>API: COMPLETED
        API-->>U: 200 OK (Results)
    end
```

### 2.3 Subscription Upgrade Flow (Stripe)
**Use Case:** User upgrades from Free to Pro.
**Key Logic:**
1.  Frontend requests a Checkout Session.
2.  API calls Stripe to generate a hosted checkout URL.
3.  User pays on Stripe.
4.  Stripe sends a webhook (`checkout.session.completed`).
5.  Django validates signature and updates DB.

```mermaid
sequenceDiagram
    actor U as User
    participant API as Django API
    participant Stripe as Stripe
    participant DB as Database

    U->>API: POST /billing/checkout-session/
    API->>Stripe: Create Session
    Stripe-->>API: URL
    API-->>U: Redirect URL

    U->>Stripe: Enters Payment Details
    Stripe->>API: POST /webhooks/stripe/ (checkout.session.completed)
    API->>API: Verify Signature
    API->>DB: Update Org Subscription (Status=ACTIVE)
    DB-->>API: Saved
    API-->>Stripe: 200 OK
```

---

## 3. 📦 Module-wise Deep Dive

### 3.1 Users Module (`apps.users`)
Handles authentication and user identity.
*   **Features:** Email-based Login, JWT Authentication, Context Awareness.

#### Critical Files
**1. `models.py`**
*   **`User` Class:**
    *   **Purpose:** Custom User model replacing Django's default.
    *   **Logic:** Removes `username` field, forces `email` as unique identifier.
    *   **Key Methods:**
        *   `get_organization()`: Helper to find the user's primary organization context based on active membership.

**2. `views.py`**
*   **`RegisterUserView` Class:**
    *   **Purpose:** Public endpoint for signup.
    *   **Logic:** Accepts email/password, creates User, returns 201.
*   **`UserMeView` Class:**
    *   **Purpose:** Session bootstrap.
    *   **Logic:** Returns User Profile **PLUS** the `active_organization` context.

### 3.2 Organizations Module (`apps.organizations`)
The backbone of multi-tenancy.
*   **Features:** RBAC (Admin/Member/Viewer), Invites, Tenant Isolation.

#### Critical Files
**1. `models.py`**
*   **`Organization` Class:**
    *   **Purpose:** The tenant root.
    *   **Fields:** `stripe_customer_id`, `subscription_status` (Free/Active/Expired).
*   **`Membership` Class:**
    *   **Purpose:** Link table for User-Org many-to-many relationship.
    *   **Fields:** `role` (ADMIN, MEMBER, VIEWER).
*   **`OrganizationInvite` Class:**
    *   **Purpose:** secure invitation system.
    *   **Logic:** Generates 32-byte hex token. Valid for 7 days.

**2. `views.py`**
*   **`OrganizationViewSet` Class:**
    *   **Purpose:** CRUD for Organizations.
    *   **Logic ENFORCED:**
        *   `perform_create`: Creator automatically becomes ADMIN.
        *   `get_queryset`: Forces filtering by `members__user=request.user` (Isolation).
    *   **Actions:**
        *   `invite_member (POST)`: Creates `OrganizationInvite`. Only ADMINs.
        *   `remove_member (DELETE)`: Deletes `Membership`. Only ADMINs. Prevents deleting Owner or Last Admin.

### 3.3 Audits Module (`apps.audits`)
The core compliance engine.
*   **Features:** Async Execution, Evidence Collection, Dashboard Aggregation.

#### Critical Files
**1. `models.py`**
*   **`Audit` Class:**
    *   **Status Workflow:** `PENDING` -> `RUNNING` -> `COMPLETED` / `FAILED`.
    *   **Fields:** `triggered_by` (User), `organization`.
*   **`Evidence` Class:**
    *   **Purpose:** Stores result of a SINGLE check (e.g., "GitHub 2FA Enabled").
    *   **Fields:** `status` (PASS/FAIL), `raw_data` (JSON dump of API response).

**2. `views.py`**
*   **`AuditStartView` Class (POST):**
    *   **Logic:**
        1.  Checks Rate Limit (default 5/hr).
        2.  Creates `Audit` (PENDING).
        3.  Starts background thread `run_audit_background`.
        4.  Returns 202 Accepted.
*   **`DashboardSummaryView` Class (GET):**
    *   **Purpose:** Executive Metrics.
    *   **Logic:** Aggregates last 30 days data.
    *   **Metrics:** Pass Rate %, Top 5 Failing Resources, Issues by Severity.

### 3.4 Billing Module (`apps.billing`)
Monetization layer via Stripe.
*   **Features:** Checkout Sessions, Webhooks, Subscription Sync.

#### Critical Files
**1. `views.py`**
*   **`BillingViewSet.checkout_session`:**
    *   **Logic:** Creates Stripe Customer (if missing), generates Stripe Checkout URL.
*   **`stripe_webhook`:**
    *   **Purpose:** Async status updates from Stripe.
    *   **Logic:**
        *   On `checkout.session.completed`: updates `subscription_status = 'active'`.
        *   On `customer.subscription.deleted`: updates `subscription_status = 'expired'`.

### 3.5 Integrations Module (`apps.integrations`)
Securely manages external access.
*   **Features:** Fernet Encryption, Key Rotation.

#### Critical Files
**1. `models.py`**
*   **`Integration` Class:**
    *   **Purpose:** Stores tokens for GitHub/AWS.
    *   **Security:** `_access_token` is a `BinaryField`.
    *   **Methods:**
        *   `access_token (getter)`: Decrypts on the fly using `services.encryption_manager`.
        *   `access_token (setter)`: Encrypts before saving.

---

## 4. 🔌 API Reference (App-wise)

*Base URL: `/api/v1`*

### 4.1 Authentication
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register/` | Create a new user account. | ❌ No |
| `POST` | `/auth/login/` | Obtain JWT Access/Refresh tokens. | ❌ No |
| `GET` | `/users/me/` | Get profile + active org context. | ✅ Yes |

### 4.2 Organizations
| Method | Endpoint | Description | Logic |
| :--- | :--- | :--- | :--- |
| `GET` | `/organizations/` | List my organizations. | Filters by `members__user=request.user` |
| `POST` | `/organizations/` | Create organization. | Creator becomes `ADMIN` |
| `POST` | `/organizations/{id}/invite_member/` | Invite a user via email. | Requires `ADMIN` role. |
| `GET` | `/organizations/{id}/members/` | List methods. | Available to all members. |

### 4.3 Audits
| Method | Endpoint | Description | Request | Response (Success) |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/audits/start/` | Start async audit. | `{}` | `{"audit_id": "...", "status": "PENDING"}` (202) |
| `GET` | `/audits/{id}/` | Get audit status. | - | `{"id": "...", "status": "COMPLETED", "score": 85}` |
| `GET` | `/audits/dashboard/summary/` | Get executive stats. | - | `{"pass_rate": 88.5, "issues": {...}}` |

### 4.4 Billing
| Method | Endpoint | Description | Request |
| :--- | :--- | :--- | :--- |
| `POST` | `/billing/checkout-session/` | Create Stripe Session. | `{"organization_id": "...", "price_id": "..."}` |
| `POST` | `/webhooks/stripe/` | Stripe Event Listener. | Stripe Signature Header |

---

## 5. 🛠️ Local Development Setup

### 5.1 Prerequisites
*   **Python 3.10+**
*   **Docker & Docker Compose** (for Redis/Postgres)
*   **Git**

### 5.2 Environment Variables (`.env`)
Create a `.env` file in `audit_ease/` based on these keys:

| Key | Description | Example Value |
| :--- | :--- | :--- |
| `DJANGO_DEBUG` | Enable debug mode (dev only). | `True` |
| `DATABASE_URL` | Config for Postgres. | `postgres://user:pass@localhost:5432/db` |
| `CELERY_BROKER_URL` | Redis URL for Task Queue. | `redis://localhost:6379/0` |
| `FERNET_KEY` | **CRITICAL**: Key for encrypting tokens. | `Use python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `STRIPE_SECRET_KEY` | Stripe Secret Key (Test Mode). | `sk_test_...` |

### 5.3 Installation Steps

**1. Clone & Virtual Env**
```bash
git clone <repo_url>
cd audit_ease
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Start Infrastructure (Docker)**
```bash
docker-compose up -d
# Starts Postgres & Redis containers
```

**3. Migrations & Run**
```bash
python manage.py migrate
python manage.py runserver
```

**4. Start Worker (Required for Audits)**
Open a new terminal:
```bash
celery -A config worker --loglevel=info
```

### 5.4 Common Errors
*   **"Fernet key must be 32 bytes"**: You forgot to generate a `FERNET_KEY`. Run the python command above.
*   **"Connection refused (Redis)"**: Ensure Docker is running and `docker-compose up` was successful.

---

## 6. 🚀 Production & Cloud Deployment

### 6.1 Preparation
1.  **Environment**: Set `DJANGO_DEBUG=False`.
2.  **Secret Management**: Use a vault (AWS Secrets Manager, etc.) for `FERNET_KEY` and `STRIPE_SECRET_KEY`.
3.  **Static Files**: Run `python manage.py collectstatic`.

### 6.2 Docker Strategy
We use a multi-stage `Dockerfile` to minimize image size.
*   **Builder Stage**: Installs build dependencies (gcc, libpq).
*   **Final Stage**: Copies only wheels and runs `gunicorn`.

**Production Command via Docker Compose:**
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```
This starts:
1.  `web`: Gunicorn WSGI server.
2.  `worker`: Celery worker for audits.
3.  `db`: PostgreSQL (with persistent volume).
4.  `redis`: Redis broker.
5.  `nginx`: Reverse proxy handling HTTPS and static files.

### 6.3 Security Checklist
*   [ ] **SSL/TLS**: Ensure Nginx is configured with Let's Encrypt or similar.
*   [ ] **Firewall**: Expose only ports 80/443. Close 5432 (DB) and 6379 (Redis).
*   [ ] **Key Rotation**: Schedule regular rotation of `FERNET_KEY` using `scripts/rotate_fernet_keys.py`.
