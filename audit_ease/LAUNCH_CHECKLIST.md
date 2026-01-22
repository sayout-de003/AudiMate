# 🚀 SaaS Launch Readiness Checklist

## Installation & Setup

### 1. Install Dependencies
```bash
cd audit_ease
pip install -r requirements.txt
# OR if using the virtual environment:
../aud/bin/pip install stripe==10.8.0
```

### 2. Create Migrations
```bash
python manage.py migrate organizations
```

### 3. Configure Environment Variables

Create or update your `.env` file:

```bash
# ===== STRIPE KEYS (Required for Production) =====
# Get these from: https://dashboard.stripe.com/test/apikeys

# Public key for frontend
STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_KEY_HERE

# Secret key for backend (keep secure!)
STRIPE_SECRET_KEY=sk_test_YOUR_KEY_HERE

# Webhook signing secret (from webhooks section in dashboard)
STRIPE_WEBHOOK_SECRET=whsec_YOUR_KEY_HERE

# ===== FRONTEND CONFIGURATION =====
# Where to redirect users after billing actions
FRONTEND_URL=http://localhost:3000

# For production:
# FRONTEND_URL=https://yourdomain.com
```

### 4. Set Up Stripe Webhooks

In your Stripe Dashboard:

1. Go to **Developers** > **Webhooks**
2. Click **Add endpoint**
3. Enter your webhook URL:
   - Development: `http://localhost:8000/api/v1/billing/webhooks/stripe/`
   - Production: `https://yourdomain.com/api/v1/billing/webhooks/stripe/`
4. Select events to listen for:
   - `checkout.session.completed`
   - `customer.subscription.deleted`
5. Reveal and copy the signing secret (starts with `whsec_`)
6. Add to `.env` as `STRIPE_WEBHOOK_SECRET=whsec_...`

---

## API Reference

### Billing Endpoints

#### Create Checkout Session
```
POST /api/v1/billing/checkout-session/

Authorization: Bearer {access_token}

Body:
{
  "organization_id": "uuid-of-organization",
  "price_id": "price_1ABC123XYZ"  // From your Stripe products
}

Response (200 OK):
{
  "checkout_url": "https://checkout.stripe.com/...",
  "session_id": "cs_..."
}

Response (403 Forbidden - Access Denied):
{
  "error": "You don't have access to this organization"
}
```

#### Stripe Webhook
```
POST /api/v1/billing/webhooks/stripe/

Headers:
  Stripe-Signature: <signature>

Body: Stripe webhook payload (automatic)

Response (200 OK):
{
  "status": "success"
}

Response (400 Bad Request - Invalid Signature):
{
  "error": "Invalid signature"
}
```

### Export Endpoint

#### Export Audit as CSV (Premium Feature)
```
GET /api/v1/audits/{audit_id}/export/csv/

Authorization: Bearer {access_token}

Response (200 OK):
- Streams CSV file with headers:
  Resource ID, Check Name, Status, Severity, Timestamp, Comment
- Content-Disposition: attachment; filename="audit_{audit_id}_{timestamp}.csv"

Response (403 Forbidden - Free Tier):
{
  "error": "Upgrade to Premium to export data"
}

Response (403 Forbidden - Wrong Organization):
{
  "error": "You don't have access to this audit"
}

Response (404 Not Found):
{
  "error": "Audit not found"
}
```

---

## Testing the Integration

### 1. Create Test Organization
```bash
# Via Django shell
python manage.py shell

from django.contrib.auth import get_user_model
from apps.organizations.models import Organization

User = get_user_model()
user = User.objects.first()  # Or create new user
org = Organization.objects.create(
    name="Test Company",
    owner=user
)
print(f"Org ID: {org.id}")
print(f"Subscription Status: {org.subscription_status}")
```

### 2. Test Checkout Session Creation
```bash
# Using curl or Postman
curl -X POST http://localhost:8000/api/v1/billing/checkout-session/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "YOUR_ORG_UUID",
    "price_id": "price_1ABC123XYZ"
  }'
```

### 3. Test CSV Export (Premium)
```bash
# Free tier - should return 403
curl -X GET http://localhost:8000/api/v1/audits/{audit_id}/export/csv/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response: {"error": "Upgrade to Premium to export data"}
```

### 4. Test CSV Export (After Upgrading)
```bash
# After subscription_status = 'active', should work
curl -X GET http://localhost:8000/api/v1/audits/{audit_id}/export/csv/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  > audit_export.csv
```

---

## Stripe Test Cards

Use these for testing in Stripe's test mode:

### Successful Payment
- Card: `4242 4242 4242 4242`
- Exp: Any future date (e.g., 12/25)
- CVC: Any 3 digits (e.g., 123)

### Declined Card
- Card: `4000 0000 0000 0002`
- Exp: Any future date
- CVC: Any 3 digits

### Subscription Test
1. Create checkout session with test `price_` ID from Stripe dashboard
2. Use 4242 card to complete payment
3. Webhook should automatically update organization status to 'active'

---

## Monitoring & Debugging

### Check Organization Subscription Status
```bash
python manage.py shell

from apps.organizations.models import Organization

org = Organization.objects.get(id='your-org-uuid')
print(f"Status: {org.subscription_status}")
print(f"Stripe Customer: {org.stripe_customer_id}")
print(f"Stripe Subscription: {org.stripe_subscription_id}")
print(f"Started: {org.subscription_started_at}")
print(f"Ends: {org.subscription_ends_at}")
```

### Verify Webhook Setup
```bash
python manage.py shell

from django.conf import settings

print(f"Webhook Secret: {settings.STRIPE_WEBHOOK_SECRET}")
print(f"Frontend URL: {settings.FRONTEND_URL}")
```

### Test Webhook Locally (Using Stripe CLI)
```bash
# Install Stripe CLI: https://stripe.com/docs/stripe-cli

# Forward webhook to local endpoint
stripe listen --forward-to localhost:8000/api/v1/billing/webhooks/stripe/

# This will output signing secret - use in .env as STRIPE_WEBHOOK_SECRET

# In another terminal, trigger test event:
stripe trigger checkout.session.completed
```

---

## Production Deployment Checklist

- [ ] Set `DEBUG = False` in settings
- [ ] Add real Stripe keys (not test keys)
- [ ] Set `STRIPE_WEBHOOK_SECRET` to production webhook secret
- [ ] Update `FRONTEND_URL` to production domain
- [ ] Configure Stripe webhooks to point to production URL
- [ ] Use production database (not SQLite)
- [ ] Set `ALLOWED_HOSTS` to production domain
- [ ] Enable SSL (`SECURE_SSL_REDIRECT = True`)
- [ ] Test entire checkout flow end-to-end
- [ ] Test webhook handling with Stripe test events
- [ ] Monitor logs for webhook failures
- [ ] Set up error alerting for webhook endpoint
- [ ] Create backup/restore procedures for Stripe data

---

## Troubleshooting

### "Stripe API Key Missing"
- Ensure `STRIPE_SECRET_KEY` is set in `.env`
- Test with `python manage.py shell` and check settings

### "Invalid Webhook Signature"
- Verify `STRIPE_WEBHOOK_SECRET` matches dashboard
- Check webhook endpoint URL in dashboard matches your app URL
- Ensure webhook events are configured correctly

### "Organization Not Found" (Webhook)
- Verify `organization_id` is in Stripe customer metadata
- Check organization UUID is valid
- Ensure organization exists in database

### CSV Export Returns 403
- Check `organization.subscription_status` is 'active'
- Verify user is member of the organization
- Ensure user has correct role (MEMBER or ADMIN)

### Webhook Not Firing
- Check Stripe dashboard for webhook delivery logs
- Verify endpoint URL is accessible and returning 200
- Check server logs for any errors
- Use Stripe CLI to test webhook delivery locally

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                     │
│              - Shows Upgrade button                     │
│              - Redirects to checkout_url               │
│              - Handles success/cancel redirects         │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │   POST /api/v1/billing/              │
        │   checkout-session/                  │
        │   (Creates Stripe Session)           │
        └────────────┬─────────────────────────┘
                     │
        ┌────────────▼──────────────────┐
        │    Stripe Checkout Page       │
        │    (Secure Payment)           │
        └────────────┬──────────────────┘
                     │
        ┌────────────▼──────────────────────────────┐
        │   Stripe Webhooks                         │
        │   (checkout.session.completed)            │
        │   (customer.subscription.deleted)         │
        └────────────┬─────────────────────────────┘
                     │
        ┌────────────▼──────────────────────────────┐
        │   POST /api/v1/billing/                  │
        │   webhooks/stripe/                       │
        │   (Updates Organization.subscription)    │
        └──────────────────────────────────────────┘
                     │
        ┌────────────▼──────────────────────────────┐
        │   Premium Features Unlocked               │
        │   GET /api/v1/audits/{id}/export/csv/    │
        │   (CSV Export with HasActiveSubscription)│
        └──────────────────────────────────────────┘
```

---

## Support & Resources

- [Stripe Documentation](https://stripe.com/docs)
- [DRF Documentation](https://www.django-rest-framework.org/)
- [Django Documentation](https://docs.djangoproject.com/)
- [Stripe Webhooks Guide](https://stripe.com/docs/webhooks)

---

## Summary

You now have a complete B2B SaaS platform with:

✅ Organizations (Teams)
✅ Stripe Billing Integration
✅ Premium Feature Gating
✅ Data Export (CSV)
✅ Webhook-based Subscription Updates
✅ Multi-tenant Data Isolation

**Ready to ship!** 🚀
