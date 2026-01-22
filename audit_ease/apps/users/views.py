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

class RegisterUserView(generics.CreateAPIView):
    """
    Endpoint for new users to register.
    Auth not required.
    """
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserRegistrationSerializer

class UserMeView(APIView):
    """
    Endpoint to get current user details + Active Org Context
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        active_org = getattr(request, 'organization', None)
        
        data = {
            "id": request.user.id,
            "email": request.user.email,
            "full_name": f"{request.user.first_name} {request.user.last_name}",
            "active_organization": {
                "id": str(active_org.id) if active_org else None,
                "name": active_org.name if active_org else None,
                "role": "MEMBER" 
            } if active_org else None
        }
        return Response(data)