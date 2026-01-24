"""
API Views for email OTP verification
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework.throttling import AnonRateThrottle

from .verification import EmailVerification
from .utils import send_verification_email, invalidate_previous_otps

User = get_user_model()


class ResendOTPThrottle(AnonRateThrottle):
    """Rate limit OTP resend to 1 per minute"""
    rate = '1/min'


@extend_schema(
    auth=[],
    summary="Verify email with OTP code",
    description="Verify user email address using 6-digit OTP code. Returns JWT tokens on success.",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'email': {'type': 'string', 'format': 'email'},
                'otp_code': {'type': 'string', 'minLength': 6, 'maxLength': 6}
            },
            'required': ['email', 'otp_code']
        }
    }
)
class VerifyEmailView(APIView):
    """
    POST /auth/verify-email/
    
    Verify user's email using OTP code.
    On success, activates account and returns JWT tokens.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        otp_code = request.data.get('otp_code')
        
        if not email or not otp_code:
            return Response(
                {'error': 'Email and OTP code are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find the user
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already verified
        if user.email_verified:
            return Response(
                {'error': 'Email already verified'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find the latest non-expired OTP
        verification = EmailVerification.objects.filter(
            user=user,
            email=email,
            is_verified=False
        ).order_by('-created_at').first()
        
        if not verification:
            return Response(
                {'error': 'No verification code found. Please request a new one.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check expiration
        if verification.is_expired():
            return Response(
                {
                    'error': 'Verification code has expired',
                    'message': 'Please request a new code'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check attempt limit
        if not verification.can_attempt():
            return Response(
                {
                    'error': 'Too many failed attempts',
                    'message': 'Please request a new code'
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # Verify OTP code
        if verification.otp_code != otp_code:
            # Increment attempt counter
            verification.attempts += 1
            verification.save(update_fields=['attempts'])
            
            attempts_remaining = 3 - verification.attempts
            return Response(
                {
                    'error': 'Invalid verification code',
                    'attempts_remaining': attempts_remaining
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Success! Mark email as verified
        with transaction.atomic():
            verification.is_verified = True
            verification.save(update_fields=['is_verified'])
            
            user.email_verified = True
            user.is_active = True
            user.save(update_fields=['email_verified', 'is_active'])
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Email verified successfully',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': str(user.id),
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        }, status=status.HTTP_200_OK)


@extend_schema(
    auth=[],
    summary="Resend OTP code",
    description="Request a new OTP code. Rate limited to 1 request per minute.",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'email': {'type': 'string', 'format': 'email'}
            },
            'required': ['email']
        }
    }
)
class ResendOTPView(APIView):
    """
    POST /auth/resend-otp/
    
    Generate and send a new OTP code.
    Rate limited to prevent abuse.
    """
    permission_classes = [AllowAny]
    throttle_classes = [ResendOTPThrottle]
    
    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find the user
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already verified
        if user.email_verified:
            return Response(
                {'error': 'Email already verified'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Invalidate previous OTPs
        invalidate_previous_otps(user)
        
        # Create new OTP
        verification = EmailVerification.create_otp(user, email)
        
        # Send email
        try:
            send_verification_email(user, verification.otp_code)
        except Exception as e:
            return Response(
                {'error': 'Failed to send email', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'message': 'New verification code sent',
            'email': email,
            'expires_in_minutes': 10
        }, status=status.HTTP_200_OK)
