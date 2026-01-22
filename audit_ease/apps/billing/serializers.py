from rest_framework import serializers
from apps.organizations.models import Organization
import uuid


class CreateCheckoutSessionSerializer(serializers.Serializer):
    """
    Serializer for creating a Stripe Checkout Session
    
    Input validation:
    - organization_id: UUID of organization (must belong to user)
    - price_id: Stripe price ID (e.g., 'price_...')
    """
    organization_id = serializers.UUIDField(required=True)
    price_id = serializers.CharField(required=True, max_length=255)
    
    def validate_organization_id(self, value):
        """Ensure organization exists"""
        try:
            Organization.objects.get(id=value)
        except Organization.DoesNotExist:
            raise serializers.ValidationError("Organization not found")
        return value
    
    def validate_price_id(self, value):
        """Basic validation for Stripe price ID format"""
        if not value.startswith('price_'):
            raise serializers.ValidationError(
                "Invalid price_id format. Must start with 'price_'"
            )
        return value
