"""
Integration Model with Secure Token Storage

Manages third-party integrations (GitHub, GitLab, Jira) with encrypted token storage.
Uses Fernet for symmetric encryption with support for key rotation.
"""

import logging
import requests
from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken
from apps.organizations.models import Organization
from apps.users.models import User
from services.encryption_manager import get_key_manager

logger = logging.getLogger(__name__)

class Integration(models.Model):
    class ProviderChoices(models.TextChoices):
        GITHUB = 'github', 'GitHub'
        # GITLAB = 'gitlab', 'GitLab'
        # JIRA = 'jira', 'Jira'
        # AWS = 'aws', 'AWS'

    class StatusChoices(models.TextChoices):
        ACTIVE = 'active', 'Active'
        DISCONNECTED = 'disconnected', 'Disconnected'
        ERROR = 'error', 'Error'

    # --- Relationships ---
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE, 
        related_name="integrations",
        null=False,
        blank=False,
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True
    )

    # --- Identity & Config ---
    name = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Friendly name (e.g., 'Engineering Team's Repo')"
    )
    provider = models.CharField(
        max_length=50, 
        choices=ProviderChoices.choices, 
        default=ProviderChoices.GITHUB
    )
    external_id = models.CharField(
        max_length=255, 
        help_text="External ID (e.g. GitHub Organization ID or Repo ID)"
    )
    config = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Store provider-specific metadata here"
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE
    )

    # --- Encrypted Storage Fields ---
    # Data stored here is automatically encrypted/decrypted with Fernet
    # The encryption manager handles key rotation transparently
    _access_token = models.BinaryField(editable=False, null=True, blank=True)
    _refresh_token = models.BinaryField(editable=False, null=True, blank=True)

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Integration"
        verbose_name_plural = "Integrations"
        # Critical: Prevent duplicate integrations for same org/provider/external-id
        unique_together = ('organization', 'provider', 'external_id')
        # Indexes for fast lookups
        indexes = [
            models.Index(fields=['organization', 'provider']),
            models.Index(fields=['created_by', 'created_at']),
        ]

    def __str__(self):
        return f"{self.organization.name} - {self.get_provider_display()} ({self.external_id})"

    # --- Encryption & Decryption ---

    @property
    def _encryption_manager(self):
        """Get the encryption manager."""
        return get_key_manager()

    def _decrypt(self, encrypted_data):
        """
        Decrypt encrypted bytes.
        Handles old keys automatically via key rotation support.
        """
        if not encrypted_data:
            return None
        try:
            return self._encryption_manager.decrypt(encrypted_data)
        except InvalidToken as e:
            logger.error(
                f"Failed to decrypt token for Integration {self.id} ({self.provider}). "
                f"Possible key corruption or data tampering. {e}"
            )
            return None
        except Exception as e:
            logger.error(f"Unexpected decryption error for Integration {self.id}: {e}")
            return None

    def _encrypt(self, plain_text):
        """
        Encrypt plaintext to bytes.
        Always uses the current primary key.
        """
        if not plain_text:
            return None
        try:
            encrypted = self._encryption_manager.encrypt(plain_text)
            return encrypted.encode('utf-8') if isinstance(encrypted, str) else encrypted
        except Exception as e:
            logger.error(f"Failed to encrypt token for Integration {self.id}: {e}")
            raise

    # --- Public Token Properties ---

    @property
    def access_token(self):
        """
        Get the decrypted access token.
        SENSITIVE: Only use in trusted contexts.
        """
        return self._decrypt(self._access_token)

    @access_token.setter
    def access_token(self, value):
        """
        Set the access token (automatically encrypted).
        """
        self._access_token = self._encrypt(value)

    @property
    def refresh_token(self):
        """Get the decrypted refresh token."""
        return self._decrypt(self._refresh_token)

    @refresh_token.setter
    def refresh_token(self, value):
        """Set the refresh token (automatically encrypted)."""
        self._refresh_token = self._encrypt(value)

    def set_token(self, token_data):
        """
        Set token data (handles dict or string).
        Automatically encrypts and stores the token.
        """
        import json
        if isinstance(token_data, dict):
            token_data = json.dumps(token_data)
        # Encrypt and store
        self.encrypted_token = self._encryption_manager.encrypt(token_data.encode())

    def validate_integration(self) -> bool:
        """
        Validate that the integration has valid credentials.
        This calls the GitHub API to verify the token.
        """
        if not self.access_token:
            logger.warning(f"Integration {self.id} has no access token")
            return False
            
        try:
            # Decrypt the token
            token = self.access_token
            
            # Make a lightweight GET request to GitHub API
            headers = {'Authorization': f'token {token}'}
            # Set a timeout to prevent hanging
            response = requests.get('https://api.github.com/user', headers=headers, timeout=10)
            
            if response.status_code == 200:
                self.status = self.StatusChoices.ACTIVE
                self.save()
                return True
                
            elif response.status_code == 401:
                logger.warning(f"Integration {self.id} token invalid/revoked (401).")
                self.status = self.StatusChoices.ERROR  # Using ERROR to represent revoked/invalid state
                self.save()
                return False
                
            else:
                # GitHub is down or other error - log but don't change status
                logger.error(f"GitHub API validation failed for Integration {self.id}. Status: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Network error validating Integration {self.id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error validating Integration {self.id}: {e}")
            return False















# from django.db import models

# # Create your models here.
# from django.db import models
# from django.conf import settings
# from cryptography.fernet import Fernet
# from apps.organizations.models import Organization
# # from organizations.models import Organization

# class Integration(models.Model):
#     PROVIDER_CHOICES = (
#         ('github', 'GitHub'),
#     )

#     organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='integrations')
#     provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES)
    
#     # We store the encrypted bytes as a CharField (base64 encoded string)
#     _access_token = models.TextField(db_column='access_token')
#     _refresh_token = models.TextField(db_column='refresh_token', blank=True, null=True)
    
#     identifier = models.CharField(max_length=255, help_text="External ID (e.g. Installation ID)")
#     meta_data = models.JSONField(default=dict, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         unique_together = ('organization', 'provider', 'identifier')

#     @property
#     def cipher(self):
#         return Fernet(settings.FERNET_KEY)

#     # --- Access Token Handling ---
#     @property
#     def access_token(self):
#         """Decrypts and returns the access token."""
#         return self.cipher.decrypt(self._access_token.encode()).decode()

#     @access_token.setter
#     def access_token(self, value):
#         """Encrypts the access token before saving."""
#         if value:
#             self._access_token = self.cipher.encrypt(value.encode()).decode()

#     # --- Refresh Token Handling ---
#     @property
#     def refresh_token(self):
#         if not self._refresh_token:
#             return None
#         return self.cipher.decrypt(self._refresh_token.encode()).decode()

#     @refresh_token.setter
#     def refresh_token(self, value):
#         if value:
#             self._refresh_token = self.cipher.encrypt(value.encode()).decode()
#         else:
#             self._refresh_token = None

#     def __str__(self):
#         return f"{self.provider} - {self.organization.name}"