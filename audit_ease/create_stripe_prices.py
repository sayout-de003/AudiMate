import os
import sys
import django
import stripe

# Setup Django environment to load settings
sys.path.append('/Users/sayantande/audit_full_app/audit_ease')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_prices():
    print(f"Using Stripe Key: {stripe.api_key[:8]}...")
    
    try:
        # 1. Create Product
        product = stripe.Product.create(
            name='AuditMate Pro',
            description='AuditMate Pro Subscription',
        )
        print(f"Created Product: {product.id}")

        # 2. Create Monthly Price ($69)
        price_monthly = stripe.Price.create(
            unit_amount=6900,
            currency='usd',
            recurring={'interval': 'month'},
            product=product.id,
            nickname='Pro Monthly',
        )
        print(f"Created Monthly Price: {price_monthly.id}")

        # 3. Create Yearly Price ($662.40 -> ~66240 cents)
        # Using 66240 for exact match to frontend calculation
        price_yearly = stripe.Price.create(
            unit_amount=66240,
            currency='usd',
            recurring={'interval': 'year'},
            product=product.id,
            nickname='Pro Yearly',
        )
        print(f"Created Yearly Price: {price_yearly.id}")
        
        print("\nSUCCESS! Update apps/billing/constants.py with these IDs:")
        print(f"price_pro_monthly = '{price_monthly.id}'")
        print(f"price_pro_yearly = '{price_yearly.id}'")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    create_prices()
