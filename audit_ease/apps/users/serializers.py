# apps/users/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True, 
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'password', 'password_confirm')
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True}
        }

    def validate_email(self, value):
        """Validate email is not already in use."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        from .verification import EmailVerification
        from .utils import send_verification_email
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Remove password_confirm as it's not a model field
        validated_data.pop('password_confirm')
        
        # Create inactive user (will be activated after email verification)
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            is_active=False,  # Inactive until email verified
            email_verified=False
        )
        
        # Generate and send OTP
        try:
            # Create OTP
            verification = EmailVerification.create_otp(user, user.email)
            
            # Send verification email
            send_verification_email(user, verification.otp_code)
            logger.info(f"Verification email sent to {user.email} with OTP: {verification.otp_code}")
        except Exception as e:
            # Log error but don't fail registration
            logger.error(f"Failed to send verification email to {user.email}: {e}")
            # Still return the user - they can request resend
        
        return user