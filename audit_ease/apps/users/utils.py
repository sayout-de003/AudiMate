"""
Utility functions for email verification and OTP management
"""
import random
import string
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings


def generate_otp(length=6):
    """
    Generate a random OTP code.
    
    Args:
        length (int): Length of OTP code (default: 6)
    
    Returns:
        str: Random numeric OTP code
    """
    return ''.join(random.choices(string.digits, k=length))


def send_verification_email(user, otp_code):
    """
    Send OTP verification email to user.
    
    Args:
        user: User instance
        otp_code (str): 6-digit OTP code
    
    Returns:
        int: Number of successfully delivered messages
    """
    context = {
        'user': user,
        'otp_code': otp_code,
        'expires_in_minutes': 10,
        'site_name': 'AuditEase'
    }
    
    # Render HTML template
    html_message = render_to_string('emails/verification_code.html', context)
    
    # Plain text fallback
    plain_message = f"""
Hi {user.first_name or user.email},

Welcome to AuditEase! Please verify your email address using the code below:

{otp_code}

This code will expire in 10 minutes.

If you didn't create an account, please ignore this email.

Best regards,
The AuditEase Team
    """.strip()
    
    return send_mail(
        subject='Verify Your Email - AuditEase',
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False
    )


def invalidate_previous_otps(user):
    """
    Invalidate all previous OTP codes for a user.
    Called when generating a new OTP.
    
    Args:
        user: User instance
    """
    from .verification import EmailVerification
    
    EmailVerification.objects.filter(
        user=user,
        is_verified=False
    ).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
