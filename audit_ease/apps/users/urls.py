# apps/users/urls.py
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import RegisterUserView, UserMeView
from .views_auth import GoogleLogin
from .verification_views import VerifyEmailView, ResendOTPView

urlpatterns = [
    # Authentication
    path('auth/register/', RegisterUserView.as_view(), name='auth_register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='auth_login'), # This acts as your Login view
    path('auth/refresh/', TokenRefreshView.as_view(), name='auth_refresh'),
    path('auth/google/', GoogleLogin.as_view(), name='google_login'),

    # Email Verification (OTP)
    path('auth/verify-email/', VerifyEmailView.as_view(), name='verify_email'),
    path('auth/resend-otp/', ResendOTPView.as_view(), name='resend_otp'),

    # Profile
    path('users/me/', UserMeView.as_view(), name='user_me'),
]
