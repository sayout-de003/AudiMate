"""
Production-Grade Encryption Key Management

Implements secure key rotation, versioning, and storage for Fernet-based encryption.
Critical for protecting GitHub tokens and other sensitive integration credentials.
"""

import logging
from datetime import datetime, timedelta
from cryptography.fernet import Fernet, MultiFernet
from django.conf import settings
from django.core.management.base import CommandError
import os

logger = logging.getLogger(__name__)


class EncryptionKeyManager:
    """
    Manages encryption keys with support for key rotation.
    
    Production strategy:
    1. Multiple keys: Primary (active) + historical keys (for decryption)
    2. Key versioning: Track which key encrypted which data
    3. Scheduled rotation: Migrate to new keys periodically
    4. Secure storage: Keys in environment variables, never in code
    
    The system uses Fernet's built-in multi-key support: data encrypted with
    old keys can still be decrypted, but new data is encrypted with the latest key.
    """
    
    # Environment variable names
    PRIMARY_KEY_ENV = 'FERNET_KEY_PRIMARY'
    ROTATION_KEYS_ENV = 'FERNET_KEYS_HISTORICAL'  # Comma-separated
    KEY_CREATED_AT_ENV = 'FERNET_KEY_CREATED_AT'
    
    # Rotation policy: rotate keys every 90 days
    KEY_ROTATION_DAYS = 90
    
    def __init__(self):
        """Initialize the key manager."""
        self.primary_key = self._load_primary_key()
        self.historical_keys = self._load_historical_keys()
        self.key_created_at = self._load_key_created_at()
        self.cipher = self._build_multi_cipher()
    
    def _load_primary_key(self) -> str:
        """Load the primary (active) encryption key from environment."""
        key = os.getenv(self.PRIMARY_KEY_ENV)
        if not key:
            # For development, generate a new key
            if settings.DEBUG:
                logger.warning("No FERNET_KEY_PRIMARY in environment. Generating development key.")
                key = Fernet.generate_key().decode('utf-8')
            else:
                raise ValueError(
                    f"CRITICAL: {self.PRIMARY_KEY_ENV} not set in production environment. "
                    "This is required for secure token storage."
                )
        return key
    
    def _load_historical_keys(self) -> list:
        """Load historical keys for decryption compatibility."""
        keys_env = os.getenv(self.ROTATION_KEYS_ENV, "")
        if not keys_env:
            return []
        # Split comma-separated keys
        return [k.strip() for k in keys_env.split(',') if k.strip()]
    
    def _load_key_created_at(self) -> datetime:
        """Load the timestamp when the primary key was created."""
        created_at_str = os.getenv(self.KEY_CREATED_AT_ENV)
        if created_at_str:
            try:
                return datetime.fromisoformat(created_at_str)
            except ValueError:
                logger.warning("Invalid FERNET_KEY_CREATED_AT format")
        return datetime.now()
    
    def _build_multi_cipher(self) -> MultiFernet:
        """
        Build a MultiFernet cipher with primary key first, then historical keys.
        MultiFernet tries to decrypt with the primary key first (newest),
        but can decrypt with any of the historical keys.
        """
        all_keys = [self.primary_key] + self.historical_keys
        # Convert strings to bytes if needed
        key_bytes = []
        for key in all_keys:
            if isinstance(key, str):
                key = key.encode('utf-8')
            key_bytes.append(key)
        
        return MultiFernet([Fernet(k) for k in key_bytes])
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext with the primary key.
        
        Args:
            plaintext: The unencrypted text
        
        Returns:
            Encrypted text as string (base64 encoded)
        """
        if not plaintext:
            return None
        
        try:
            # Use only the primary key for encryption (Fernet, not MultiFernet)
            primary_cipher = Fernet(self.primary_key.encode() if isinstance(self.primary_key, str) else self.primary_key)
            encrypted = primary_cipher.encrypt(plaintext.encode('utf-8'))
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext with any available key (primary or historical).
        
        Args:
            ciphertext: The encrypted text
        
        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return None
        
        try:
            if isinstance(ciphertext, str):
                ciphertext = ciphertext.encode('utf-8')
            
            # MultiFernet tries primary key first, then historical keys
            decrypted = self.cipher.decrypt(ciphertext)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def should_rotate_key(self) -> bool:
        """
        Check if the primary key should be rotated based on age.
        
        Returns:
            True if key is older than KEY_ROTATION_DAYS
        """
        age = datetime.now() - self.key_created_at
        return age > timedelta(days=self.KEY_ROTATION_DAYS)
    
    def rotate_key(self) -> str:
        """
        Perform key rotation:
        1. Move current primary key to historical keys
        2. Generate new primary key
        3. Update environment variables
        4. Log the event for audit trail
        
        Returns:
            The new primary key
        
        Note: After rotation, you MUST update environment variables
        and restart the application for changes to take effect.
        """
        logger.warning("=== INITIATING KEY ROTATION ===")
        
        # Move current primary to historical
        new_historical = [self.primary_key] + self.historical_keys
        
        # Generate new primary key
        new_primary = Fernet.generate_key().decode('utf-8')
        
        # Log rotation details (for audit trail)
        logger.info(
            f"Key rotation completed. "
            f"Old key archived. New key generated. "
            f"Rotation timestamp: {datetime.now().isoformat()}"
        )
        
        # Return instructions for environment update
        instructions = {
            'new_primary_key': new_primary,
            'historical_keys': new_historical,
            'rotation_time': datetime.now().isoformat(),
            'env_update_commands': [
                f"export {self.PRIMARY_KEY_ENV}='{new_primary}'",
                f"export {self.ROTATION_KEYS_ENV}='{','.join(new_historical)}'",
                f"export {self.KEY_CREATED_AT_ENV}='{datetime.now().isoformat()}'",
            ]
        }
        
        return instructions
    
    def get_key_status(self) -> dict:
        """
        Get current key status for monitoring and audit purposes.
        
        Returns:
            Dictionary with key age, rotation status, etc.
        """
        age = datetime.now() - self.key_created_at
        should_rotate = self.should_rotate_key()
        
        return {
            'primary_key_set': bool(self.primary_key),
            'historical_keys_count': len(self.historical_keys),
            'key_age_days': age.days,
            'rotation_required': should_rotate,
            'days_until_rotation': max(0, self.KEY_ROTATION_DAYS - age.days),
            'created_at': self.key_created_at.isoformat(),
        }


# Singleton instance
_key_manager = None


def get_key_manager() -> EncryptionKeyManager:
    """Get the encryption key manager singleton."""
    global _key_manager
    if _key_manager is None:
        _key_manager = EncryptionKeyManager()
    return _key_manager
