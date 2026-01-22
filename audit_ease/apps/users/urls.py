# apps/users/urls.py
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import RegisterUserView, UserMeView

urlpatterns = [
    # Authentication
    path('auth/register/', RegisterUserView.as_view(), name='auth_register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='auth_login'), # This acts as your Login view
    path('auth/refresh/', TokenRefreshView.as_view(), name='auth_refresh'),

    # Profile
    path('users/me/', UserMeView.as_view(), name='user_me'),
]
