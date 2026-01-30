# B2B SaaS Architecture Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Frontend (React/Vue)                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │  Dashboard       │  │  Billing Page    │  │  Export Feature  │   │
│  │  ✓ View Audits   │  │  ✓ Upgrade Btn   │  │  ✓ Download CSV  │   │
│  │  ✓ Manage Team   │  │  ✓ Status Page   │  │  ✓ Export Btn    │   │ 
│  └──────────────────┘  └──────────────────┘  └──────────────────┘   │
└────────────┬─────────────────────┬──────────────────────┬───────────┘
             │                     │                      │
             ▼                     ▼                      ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Django REST API Backend                           │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ Authentication Layer                                           │  │
│  │ JWT Token-based + Session-based Auth                           │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────────┤  │
│  │ Organizations   │  │ Billing Engine   │  │ Audits & Export     │  │
│  │ Endpoints       │  │ Endpoints        │  │ Endpoints           │  │
│  │                 │  │                  │  │                     │  │
│  │ • List Orgs     │  │ POST checkout-   │  │ • GET /audits/      │  │
│  │ • Create Org    │  │ session/         │  │ • GET /export/csv/  │  │
│  │ • Invite Member │  │                  │  │   (Premium Only)    │  │
│  │ • Accept Invite │  │ POST webhooks/   │  │                     │  │
│  │                 │  │ stripe/ (no auth)│  │                     │  │
│  └─────────────────┘  └──────────────────┘  └─────────────────────┤  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ Permission & Authorization Layer                               │  │
│  │                                                                │  │
│  │ ✓ IsAuthenticated        - User is logged in                   │  │
│  │ ✓ IsSameOrganization     - User is in audit's org              │  │
│  │ ✓ IsOrgAdmin             - User is org admin                   │  │
│  │ ✓ HasActiveSubscription  - Org subscription is active          │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
             │                     │                      │
             ▼                     ▼                      ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     Database Layer (PostgreSQL)                      │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐    │
│  │ Organizations│  │ Stripe Data  │  │ Audits & Evidence        │    │
│  │              │  │              │  │                          │     
│  │ • id (UUID)  │  │ • customer_id│  │ • audit_id (UUID)        │    │
│  │ • name       │  │ • sub_id     │  │ • evidence (many)        │    │
│  │ • owner      │  │              │  │ • status (PASS/FAIL)     │    │
│  │ • created_at │  │              │  │ • created_at             │    │
│  │              │  │ Subscription │  │                          │    │
│  │ NEW:         │  │              │  │                          │    │
│  │ • sub_status │  │ • status     │  │                          │    │
│  │ • stripe_cust│  │ • started_at │  │                          │    │
│  │ • stripe_sub │  │ • ends_at    │  │                          │    │
│  │ • started_at │  │              │  │                          │    │
│  │ • ends_at    │  │              │  │                          │    │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘    │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐                                  │
│  │ Users        │  │ Memberships  │                                  │
│  │              │  │              │                                  │
│  │ • id (UUID)  │  │ • user_id    │ Many-to-Many                     │
│  │ • email      │  │ • org_id     │ User → Org                       │
│  │ • password   │  │ • role       │ (ADMIN, MEMBER, VIEWER)          │
│  │ • created_at │  │ • joined_at  │                                  │
│  └──────────────┘  └──────────────┘                                  │
└──────────────────────────────────────────────────────────────────────┘
             │                     │                      │
             ▼                     ▼                      ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    External Services (Stripe)                        │
│                                                                      │
│  ┌──────────────────┐        ┌──────────────────────────────────┐    │
│  │ Stripe Checkout  │        │ Stripe Webhooks                  │    │
│  │ Page             │        │ Events:                          │    │
│  │                  │        │ ✓ checkout.session.completed     │    │
│  │ • Payment Form   │        │ ✓ customer.subscription.deleted  │    │
│  │ • Card Entry     │        │                                  │    │
│  │ • 3D Secure      │        │ → Update Django DB               │    │
│  └──────────────────┘        └──────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Request Flow Diagram

### Scenario 1: Free User Tries to Export (Blocked)

```
┌─────────────────┐
│ Free Tier User  │
│ (no subscription)│
└────────┬────────┘
         │
         │ GET /api/v1/audits/{id}/export/csv/
         │ Authorization: Bearer token
         │
         ▼
┌──────────────────────────────────────┐
│ Django Permission Checks:            │
│ 1. IsAuthenticated ✓ (has token)     │
│ 2. IsSameOrganization ✓ (in org)     │
│ 3. HasActiveSubscription ✗ (NO!)     │
│    - Org.subscription_status = 'free'│
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────┐
│ 403 Forbidden Response       │
│ {                            │
│   "error": "Upgrade to       │
│   Premium to export data"    │
│ }                            │
└──────────────────────────────┘
```

### Scenario 2: Premium User Exports (Allowed)

```
┌──────────────────┐
│ Premium User     │
│ (active subscr.) │
└────────┬─────────┘
         │
         │ GET /api/v1/audits/{id}/export/csv/
         │ Authorization: Bearer token
         │
         ▼
┌──────────────────────────────────────┐
│ Django Permission Checks:            │
│ 1. IsAuthenticated ✓                 │
│ 2. IsSameOrganization ✓              │
│ 3. HasActiveSubscription ✓ (YES!)    │
│    - Org.subscription_status='active'│
└────────┬───────────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Query Evidence:                  │
│ Evidence.filter(audit=audit)     │
│ .select_related('question')      │
└────────┬───────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Generate CSV Stream:             │
│ Headers:                         │
│ Resource ID, Check Name, Status, │
│ Severity, Timestamp, Comment     │
└────────┬───────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ 200 OK with CSV File             │
│ Content-Type: text/csv           │
│ Content-Disposition: attachment; │
│ filename=audit_{id}_{ts}.csv     │
└──────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Browser Downloads CSV File       │
│ User saves: audit_{id}_....csv   │
└──────────────────────────────────┘
```

### Scenario 3: Checkout & Subscription Flow

```
┌────────────────────┐
│ Free User Clicks   │
│ "Upgrade to        │
│ Premium" Button    │
└────────┬───────────┘
         │
         │ POST /api/v1/billing/checkout-session/
         │ {
         │   "organization_id": "uuid",
         │   "price_id": "price_..."
         │ }
         │
         ▼
┌──────────────────────────────────┐
│ BillingViewSet.checkout_session()│
│                                  │
│ 1. Verify user in org ✓          │
│ 2. Create Stripe Customer (if    │
│    not exists)                   │
│ 3. Create Checkout Session       │
│ 4. Store org.stripe_customer_id  │
└────────┬────────────────────────────┘
         │
         ▼
┌───────────────────────────────────┐
│ 200 OK Response                   │
│ {                                 │
│   "checkout_url": "https://....", │
│   "session_id": "cs_..."          │
│ }                                 │
└────────┬────────────────────────────┘
         │
         │ Redirect to checkout_url
         │
         ▼
┌───────────────────────────────────┐
│ Stripe Checkout Page              │
│                                   │
│ 1. User enters payment details    │
│ 2. Stripe verifies card           │
│ 3. Charges subscription price     │
│ 4. Creates subscription in Stripe │
└────────┬────────────────────────────┘
         │
         │ Stripe sends webhook
         │ POST /api/v1/billing/webhooks/stripe/
         │ {
         │   "type": "checkout.session.completed",
         │   "data": {
         │     "object": {
         │       "subscription": "sub_..."
         │     }
         │   }
         │ }
         │
         ▼
┌───────────────────────────────────┐
│ stripe_webhook() Handler          │
│                                   │
│ 1. Verify signature ✓             │
│ 2. Extract organization_id        │
│ 3. Get Stripe subscription        │
│ 4. Update Organization:           │
│    • subscription_status='active' │
│    • stripe_subscription_id=sub.. │
│    • subscription_started_at=now  │
│    • subscription_ends_at=...     │
└────────┬────────────────────────────┘
         │
         ▼
┌───────────────────────────────────┐
│ 200 OK Response                   │
│ {"status": "success"}             │
└───────────────────────────────────┘

User now has PREMIUM ACCESS! ✅
CSV Export endpoint now works ✅
```

---

## Permission Matrix

| Endpoint | Free User | Premium User | Non-Member |
|----------|-----------|--------------|-----------|
| GET /audits/ | ✅ | ✅ | ❌ |
| POST /audits/start/ | ✅ | ✅ | ❌ |
| GET /audits/{id}/ | ✅ | ✅ | ❌ |
| GET /audits/{id}/export/csv/ | ❌ 403 | ✅ | ❌ 403 |
| POST /billing/checkout/ | ✅ | ✅ | ❌ |
| POST /organizations/ | ✅ | ✅ | ✅ |
| PUT /organizations/{id}/ | ✅ (own org) | ✅ (own org) | ❌ |

---

## Data Flow: A User's Journey

```
STEP 1: Sign Up
  User → Django → Create User + Auto-create Organization
  
STEP 2: Create Team
  User → Django → Create Membership (ADMIN)
  
STEP 3: Invite Team Member
  User → Django → Create OrganizationInvite + Log token
  
STEP 4: Team Member Accepts
  TeamMember + token → Django → Create Membership (MEMBER)
  
STEP 5: Run Audit
  Member → Django → Create Audit + Evidence records
  
STEP 6: Upgrade to Premium
  User → Django → POST checkout-session/
  User → Stripe → Enter payment details
  Stripe → Django → POST webhooks/stripe/
  Django → Update org.subscription_status = 'active'
  
STEP 7: Export Data (Premium)
  Member → Django → GET /export/csv/
  Django → HasActiveSubscription ✓
  Django → Generate & stream CSV
  Member → Download file
```

---

## Security Layers Visualization

```
┌─────────────────────────────────────────────────────────┐
│                 HTTP Request                            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │ Layer 1: Auth          │
        │ IsAuthenticated        │
        │ (User logged in?)      │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │ Layer 2: Organization Isolation│
        │ IsSameOrganization             │
        │ (User in org?)                 │
        └────────────┬────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │ Layer 3: Feature Gate          │
        │ HasActiveSubscription          │
        │ (Org has active sub?)          │
        └────────────┬────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │ View Logic                     │
        │ (Safely access data)           │
        └────────────┬────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │ HTTP 200 OK                    │
        │ (Secure response)              │
        └────────────────────────────────┘
```

---

## Module Dependencies

```
apps/billing/
  ├── views.py
  │   ├── imports: stripe, django, rest_framework
  │   ├── imports: apps.organizations.models
  │   └── imports: apps.organizations.permissions
  │
  ├── serializers.py
  │   ├── imports: rest_framework
  │   └── imports: apps.organizations.models
  │
  └── urls.py
      ├── imports: django.urls
      └── imports: views

apps/audits/
  ├── views_export.py
  │   ├── imports: csv, logging, django
  │   ├── imports: rest_framework
  │   ├── imports: apps.audits.models
  │   └── imports: apps.organizations.permissions
  │
  └── urls.py
      ├── imports: views_export

apps/organizations/
  └── permissions.py
      ├── imports: rest_framework
      └── imports: apps.organizations.models

config/
  ├── settings/base.py
  │   ├── INSTALLED_APPS += 'apps.billing'
  │   ├── STRIPE_PUBLISHABLE_KEY
  │   ├── STRIPE_SECRET_KEY
  │   ├── STRIPE_WEBHOOK_SECRET
  │   └── FRONTEND_URL
  │
  └── urls.py
      └── path('api/v1/billing/', include(...))
```

---

## Stripe Integration Points

```
Stripe Dashboard
    │
    ├─ API Keys (test/live)
    │  └─ STRIPE_SECRET_KEY
    │  └─ STRIPE_PUBLISHABLE_KEY
    │
    ├─ Products & Prices
    │  └─ price_xxx (monthly subscription)
    │
    └─ Webhooks
       ├─ Endpoint: POST /api/v1/billing/webhooks/stripe/
       ├─ Events:
       │  ├─ checkout.session.completed
       │  │  └─ handle_checkout_session_completed()
       │  │     └─ Update org.subscription_status='active'
       │  │
       │  └─ customer.subscription.deleted
       │     └─ handle_subscription_deleted()
       │        └─ Update org.subscription_status='expired'
       │
       └─ Signing Secret
          └─ STRIPE_WEBHOOK_SECRET
```

---

Generated: January 22, 2026
