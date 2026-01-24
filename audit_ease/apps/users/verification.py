import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.conf import settings


class EmailVerification(models.Model):
    """
    Stores email verification OTP codes for user registration.
    Each OTP is valid for 10 minutes and allows max 3 attempts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_verifications'
    )
    email = models.EmailField(db_index=True)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email Verification'
        verbose_name_plural = 'Email Verifications'
        indexes = [
            models.Index(fields=['email', '-created_at']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"OTP for {self.email} - {'Verified' if self.is_verified else 'Pending'}"
    
    def is_expired(self):
        """Check if OTP has expired"""
        return timezone.now() > self.expires_at
    
    def can_attempt(self):
        """Check if more attempts are allowed"""
        return self.attempts < 3
    
    @classmethod
    def create_otp(cls, user, email):
        """Create a new OTP for a user"""
        import random
        import string
        
        # Generate 6-digit code
        otp_code = ''.join(random.choices(string.digits, k=6))
        
        # Set expiration to 10 minutes from now
        expires_at = timezone.now() + timedelta(minutes=10)
        
        return cls.objects.create(
            user=user,
            email=email,
            otp_code=otp_code,
            expires_at=expires_at
        )
    
    @classmethod
    def cleanup_old_otps(cls):
        """Delete OTPs older than 24 hours"""
        cutoff = timezone.now() - timedelta(hours=24)
        cls.objects.filter(created_at__lt=cutoff).delete()
