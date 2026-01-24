from django.shortcuts import render

# Create your views here.
# apps/users/views.py
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth import get_user_model

from .serializers import UserRegistrationSerializer

User = get_user_model()

from drf_spectacular.utils import extend_schema

@extend_schema(auth=[], summary="Register a new user")
class RegisterUserView(generics.CreateAPIView):
    """
    Endpoint for new users to register.
    Creates inactive user and sends verification email.
    """
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserRegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            'message': 'Registration successful. Please check your email for verification code.',
            'email': user.email
        }, status=status.HTTP_201_CREATED)

class UserMeView(APIView):
    """
    Endpoint to get current user details + Active Org Context + Organizations List
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.organizations.models import Membership
        
        active_org = getattr(request, 'organization', None)
        
        # Get all organizations the user is a member of
        memberships = Membership.objects.filter(user=request.user).select_related('organization')
        organizations = [
            {
                "id": str(membership.organization.id),
                "name": membership.organization.name,
                "role": membership.role
            }
            for membership in memberships
        ]
        
        data = {
            "id": request.user.id,
            "email": request.user.email,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "full_name": f"{request.user.first_name} {request.user.last_name}",
            "current_organization": str(active_org.id) if active_org else None,
            "organizations": organizations,
            "active_organization": {
                "id": str(active_org.id) if active_org else None,
                "name": active_org.name if active_org else None,
                "role": "MEMBER" 
            } if active_org else None
        }
        return Response(data)