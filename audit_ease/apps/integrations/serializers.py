from rest_framework import serializers
from .models import Integration

class IntegrationSerializer(serializers.ModelSerializer):
    """
    Serializer for Integration model.
    Enforces strict rules:
    1. Provider must be 'github' (V1 guardrail).
    2. Input is validated but some fields are read-only.
    """
    
    # Explicitly enforce provider to be 'github' in the schema.
    # We remove read_only=True so that we can validate incorrect inputs (e.g. 'gitlab')
    provider = serializers.CharField(default='github', required=False)
    
    class Meta:
        model = Integration
        fields = [
            'id', 
            'organization', 
            'provider', 
            'name', 
            'external_id', 
            'config', 
            'status', 
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'organization', 'status']

    def validate_provider(self, value):
        """
        Extra guardrail: ensure provider is github if passed manually.
        """
        if value and value != 'github':
            raise serializers.ValidationError("Provider not supported in V1. Only 'github' is allowed.")
        return value

    def create(self, validated_data):
        """
        Strictly force provider='github' when creating.
        """
        validated_data['provider'] = 'github'
        return super().create(validated_data)
