import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
from .managers import CustomUserManager  # We will define this next

class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model using Email as the unique identifier instead of username.
    ID is a UUID to prevent enumeration attacks.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True, db_index=True)
    # full_name = models.CharField(_('full name'), max_length=255, blank=True)
    first_name = models.CharField(_('first name'), max_length=150, blank=True)
    middle_name = models.CharField(_('middle name'), max_length=150, blank=True, null=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    
    is_staff = models.BooleanField(default=False)  # For Admin panel access
    is_active = models.BooleanField(default=True)  # Soft delete flag
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Email & Password are required by default

    objects = CustomUserManager()

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']

    def __str__(self):
        return self.email

    def get_organization(self):
        """
        Get the user's primary organization.
        Used for request context and permission checks.
        
        In the future, this could support multi-org users.
        """
        from apps.organizations.models import Membership
        
        try:
            membership = Membership.objects.get(user=self)
            return membership.organization
        except Membership.DoesNotExist:
            return None
        except Membership.MultipleObjectsReturned:
            # If user is in multiple orgs, return the first one
            # In production, could return the "default" or use request context
            return Membership.objects.filter(user=self).first().organization