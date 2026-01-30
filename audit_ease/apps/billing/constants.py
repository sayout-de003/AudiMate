"""
Billing Constants and Configuration
"""

# Pricing Plans
PLAN_FREE = 'free'
PLAN_PRO = 'pro'

# Stripe Price IDs (Replace these with actual Stripe IDs in production/settings)
# For now we use string constants that should match what the frontend sends
# In a real app, these would come from settings.py or environment variables
STRIPE_PRICE_IDS = {
    'price_pro_monthly': 'price_1SuorrKCgImww2vpeZbv0eBN',
    'price_pro_yearly': 'price_1SuorsKCgImww2vpnvwwxQYD',
}

# Plan Details for reference/API responses if needed
PLANS = {
    PLAN_FREE: {
        'name': 'Free',
        'price': 0,
        'description': 'For small teams getting started',
        'features': [
            'Up to 3 historical audits',
            'Communuity Support',
            'Basic Reports'
        ]
    },
    PLAN_PRO: {
        'name': 'Pro',
        'price_monthly': 69,
        'price_yearly': 662.40, # 69 * 12 * 0.8
        'description': 'For growing businesses requiring compliance',
        'features': [
            'Unlimited audits',
            'Priority Support',
            'Advanced Reporting',
            'Historical Data',
            'API Access'
        ]
    }
}
