# Quick Reference Card

## 🚀 30-Second Setup

```bash
# Install
pip install stripe==10.8.0

# Migrate
python manage.py migrate organizations

# Configure .env
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
FRONTEND_URL=http://localhost:3000

# Done! ✅
```

---

## 📍 Key Endpoints

### Billing
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | /api/v1/billing/checkout-session/ | ✅ | Create Stripe checkout |
| POST | /api/v1/billing/webhooks/stripe/ | ❌ | Stripe events |

### Audits (Premium)
| Method | Endpoint | Auth | Permission |
|--------|----------|------|-----------|
| GET | /api/v1/audits/{id}/export/csv/ | ✅ | HasActiveSubscription |

---

## 🔑 Environment Variables

```bash
# Required for Production
STRIPE_PUBLISHABLE_KEY
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
FRONTEND_URL

# Optional (have defaults)
# None - all required
```

---

## 🛡️ Permission Classes

```python
# Import from apps.organizations.permissions

IsAuthenticated          # User logged in
IsSameOrganization     # User in org
IsOrgAdmin             # User is admin
HasActiveSubscription  # Org has active subscription
```

## Usage

```python
from rest_framework.decorators import permission_classes
from apps.organizations.permissions import HasActiveSubscription

@permission_classes([IsAuthenticated, HasActiveSubscription])
def premium_feature(request):
    pass
```

---

## 📊 Database Fields Added

**Organization model:**
```python
subscription_status         # 'free'|'active'|'expired'|'canceled'
stripe_customer_id         # Stripe Customer ID
stripe_subscription_id     # Stripe Subscription ID
subscription_started_at    # When active
subscription_ends_at       # When expires
```

---

## 🧪 Test Stripe Cards

| Card | Status | CVC | Exp |
|------|--------|-----|-----|
| 4242 4242 4242 4242 | ✅ Success | Any | Future |
| 4000 0000 0000 0002 | ❌ Declined | Any | Future |

---

## ⚙️ Configuration Defaults

```python
# settings/base.py

STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", 
                             default="pk_test_placeholder")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", 
                        default="sk_test_placeholder")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", 
                            default="whsec_placeholder")
FRONTEND_URL = env("FRONTEND_URL", 
                   default="http://localhost:3000")
```

---

## 🔄 Webhook Events Handled

| Event | Handler | Action |
|-------|---------|--------|
| checkout.session.completed | handle_checkout_session_completed() | Update org → 'active' |
| customer.subscription.deleted | handle_subscription_deleted() | Update org → 'expired' |

---

## 📝 Error Codes

| Status | Error | Meaning |
|--------|-------|---------|
| 401 | Unauthorized | Not logged in |
| 403 | Forbidden | Free tier OR wrong org |
| 404 | Not Found | Audit doesn't exist |
| 400 | Bad Request | Invalid price_id format |
| 500 | Server Error | Stripe API error |

---

## 💡 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| "Stripe API key missing" | Add STRIPE_SECRET_KEY to .env |
| "Invalid webhook signature" | Check STRIPE_WEBHOOK_SECRET matches dashboard |
| "Org not found" in webhook | Verify stripe_customer_id has organization_id metadata |
| CSV export returns 403 | Check organization.subscription_status == 'active' |
| Webhook not firing | Verify endpoint URL in Stripe dashboard |

---

## 🎯 Testing Checklist

- [ ] Create org and user
- [ ] POST /checkout-session/ returns checkout_url
- [ ] Click checkout_url (Stripe page loads)
- [ ] Complete payment with test card
- [ ] Webhook received (check logs)
- [ ] org.subscription_status → 'active'
- [ ] GET /export/csv/ now works
- [ ] Free user gets 403 for /export/csv/

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| SAAS_TRANSFORMATION.md | Complete implementation guide |
| LAUNCH_CHECKLIST.md | Setup & deployment guide |
| IMPLEMENTATION_SUMMARY.md | What was built |
| ARCHITECTURE.md | System design & diagrams |
| This file | Quick reference |

---

## 🔐 Security Checklist

- [ ] Webhook signature verification enabled
- [ ] STRIPE_SECRET_KEY is test key (dev) or live key (prod)
- [ ] HasActiveSubscription permission applied to export
- [ ] Users can't access other org's audits
- [ ] Free tier can't export data
- [ ] Stripe keys not in version control

---

## 🚀 Deployment Checklist

- [ ] Set STRIPE_SECRET_KEY to live key (not test)
- [ ] Set STRIPE_WEBHOOK_SECRET to live webhook secret
- [ ] Update FRONTEND_URL to production domain
- [ ] Enable SSL (SECURE_SSL_REDIRECT = True)
- [ ] Configure Stripe webhooks to production URL
- [ ] Monitor webhook delivery logs
- [ ] Test checkout flow end-to-end
- [ ] Add error alerting for webhook failures

---

## 💰 Monetization Patterns

### Free Tier
- Audits: ✅
- Results: ✅
- Export: ❌

### Premium Tier
- Audits: ✅
- Results: ✅
- Export: ✅

### How to Gate Features

```python
# Option 1: View decorator
@permission_classes([HasActiveSubscription])

# Option 2: ViewSet
permission_classes = [HasActiveSubscription]

# Option 3: Custom logic
if request.user_organization.subscription_status != 'active':
    return Response({
        'error': 'Upgrade to Premium'
    }, status=403)
```

---

## 📞 Support Resources

- Stripe Docs: https://stripe.com/docs
- Django Docs: https://docs.djangoproject.com
- DRF Docs: https://www.django-rest-framework.org
- Stripe CLI: https://stripe.com/docs/stripe-cli

---

## ✨ Summary

**You built:**
- ✅ Multi-tenant organizations
- ✅ Stripe subscription billing
- ✅ Premium feature gating
- ✅ CSV data export
- ✅ Webhook-based updates
- ✅ Secure data isolation

**With:**
- ✅ Standard Django patterns
- ✅ Industry best practices
- ✅ Production-ready code
- ✅ Comprehensive docs

**Now:**
- Set Stripe keys in `.env`
- Deploy to production
- Watch revenue grow 📈

---

**Generated:** January 22, 2026
**Status:** ✅ Production Ready
