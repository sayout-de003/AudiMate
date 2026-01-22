"""
Billing API Views - Stripe Integration

Endpoints:
- POST /api/billing/checkout/ - Create a Stripe Checkout Session
- POST /api/webhooks/stripe/ - Stripe webhook handler
"""

import stripe
import logging
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.organizations.models import Organization
from apps.organizations.permissions import IsSameOrganization, IsOrgAdmin
from .serializers import CreateCheckoutSessionSerializer

logger = logging.getLogger(__name__)

# Configure Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY


class BillingViewSet(viewsets.ViewSet):
    """
    Billing and Subscription Management
    
    POST /api/billing/checkout-session/
        - Create a Stripe Checkout Session for subscription
        - Required: organization_id, price_id
        - Returns: checkout URL for frontend redirect
    """
    permission_classes = [IsAuthenticated, IsSameOrganization]

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def checkout_session(self, request):
        """
        Create a Stripe Checkout Session
        
        Input (JSON):
        {
            "organization_id": "uuid",
            "price_id": "price_..." (e.g., Stripe price ID)
        }
        
        Returns:
        {
            "checkout_url": "https://checkout.stripe.com/..."
        }
        """
        serializer = CreateCheckoutSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        organization_id = serializer.validated_data['organization_id']
        price_id = serializer.validated_data.get('price_id')
        
        # Verify user has access to this organization
        try:
            org = Organization.objects.get(id=organization_id)
            # Check if user is member of this org
            if not org.members.filter(user=request.user).exists():
                return Response(
                    {"error": "You don't have access to this organization"},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Organization.DoesNotExist:
            return Response(
                {"error": "Organization not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # If organization doesn't have a Stripe customer yet, create one
            if not org.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=request.user.email,
                    metadata={
                        'organization_id': str(org.id),
                        'organization_name': org.name,
                    }
                )
                org.stripe_customer_id = customer.id
                org.save(update_fields=['stripe_customer_id'])
                logger.info(f"Created Stripe customer {customer.id} for org {org.name}")
            
            # Create a Stripe Checkout Session
            checkout_session = stripe.checkout.Session.create(
                mode='subscription',
                customer=org.stripe_customer_id,
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                success_url=f"{settings.FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.FRONTEND_URL}/billing/cancel",
                metadata={
                    'organization_id': str(org.id),
                }
            )
            
            logger.info(
                f"Created Stripe checkout session {checkout_session.id} "
                f"for org {org.name}"
            )
            
            return Response({
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id
            }, status=status.HTTP_200_OK)
        
        except stripe.error.InvalidRequestError as e:
            logger.error(f"Stripe InvalidRequestError: {str(e)}")
            return Response(
                {"error": f"Invalid Stripe request: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except stripe.error.AuthenticationError as e:
            logger.error(f"Stripe AuthenticationError: {str(e)}")
            return Response(
                {"error": "Stripe authentication failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"Unexpected error creating checkout session: {str(e)}")
            return Response(
                {"error": "Failed to create checkout session"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@csrf_exempt
@require_http_methods(["POST"])
def stripe_webhook(request):
    """
    Stripe Webhook Handler
    
    Listens for:
    - checkout.session.completed: Subscription activated
    - customer.subscription.deleted: Subscription canceled
    
    SECURITY: Verifies webhook signature using STRIPE_WEBHOOK_SECRET
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    if not sig_header:
        logger.warning("Stripe webhook received without signature header")
        return JsonResponse({'error': 'Missing signature'}, status=400)
    
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Webhook payload invalid: {str(e)}")
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Webhook signature verification failed: {str(e)}")
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    
    # Handle checkout.session.completed
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_session_completed(session)
    
    # Handle customer.subscription.deleted
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)
    
    # Log unhandled events for debugging
    else:
        logger.debug(f"Unhandled webhook event type: {event['type']}")
    
    return JsonResponse({'status': 'success'}, status=200)


def handle_checkout_session_completed(session):
    """
    Handle checkout.session.completed event
    
    Update organization subscription status to 'active'
    """
    try:
        organization_id = session.get('metadata', {}).get('organization_id')
        if not organization_id:
            logger.warning(f"No organization_id in checkout session {session.id}")
            return
        
        org = Organization.objects.get(id=organization_id)
        
        # Get subscription details
        subscription = stripe.Subscription.retrieve(session.subscription)
        
        # Update organization
        org.subscription_status = Organization.SUBSCRIPTION_STATUS_ACTIVE
        org.stripe_subscription_id = subscription.id
        org.subscription_started_at = timezone.now()
        
        # Set end date based on subscription period
        current_period_end = subscription.current_period_end
        org.subscription_ends_at = timezone.datetime.fromtimestamp(
            current_period_end,
            tz=timezone.utc
        )
        
        org.save(update_fields=[
            'subscription_status',
            'stripe_subscription_id',
            'subscription_started_at',
            'subscription_ends_at'
        ])
        
        logger.info(
            f"Updated org {org.name} subscription to active. "
            f"Stripe subscription: {subscription.id}"
        )
    except Organization.DoesNotExist:
        logger.error(f"Organization not found for checkout session: {session.id}")
    except stripe.error.InvalidRequestError as e:
        logger.error(f"Stripe error in checkout handler: {str(e)}")
    except Exception as e:
        logger.error(f"Error handling checkout session: {str(e)}")


def handle_subscription_deleted(subscription):
    """
    Handle customer.subscription.deleted event
    
    Update organization subscription status to 'expired'
    """
    try:
        # Retrieve the customer to get organization_id from metadata
        customer = stripe.Customer.retrieve(subscription.customer)
        organization_id = customer.get('metadata', {}).get('organization_id')
        
        if not organization_id:
            logger.warning(f"No organization_id in customer {customer.id}")
            return
        
        org = Organization.objects.get(id=organization_id)
        
        # Update organization
        org.subscription_status = Organization.SUBSCRIPTION_STATUS_EXPIRED
        org.subscription_ends_at = timezone.now()
        org.save(update_fields=['subscription_status', 'subscription_ends_at'])
        
        logger.info(f"Marked org {org.name} subscription as expired")
    except Organization.DoesNotExist:
        logger.error(f"Organization not found for subscription: {subscription.id}")
    except stripe.error.InvalidRequestError as e:
        logger.error(f"Stripe error in subscription handler: {str(e)}")
    except Exception as e:
        logger.error(f"Error handling subscription deletion: {str(e)}")
