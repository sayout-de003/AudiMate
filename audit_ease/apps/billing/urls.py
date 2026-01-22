from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BillingViewSet, stripe_webhook

# Router for ViewSet actions
router = DefaultRouter()
router.register(r'', BillingViewSet, basename='billing')

urlpatterns = [
    # Billing API routes
    path('', include(router.urls)),
    
    # Stripe Webhook (separate endpoint, no auth required)
    path('webhooks/stripe/', stripe_webhook, name='stripe_webhook'),
]
