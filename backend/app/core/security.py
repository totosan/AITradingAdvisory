"""
Secure secrets management with Fernet encryption.

Features:
- AES-256 encryption (via Fernet)
- Key generation and secure storage
- Atomic file operations
- No secrets in logs or errors

Usage:
    vault = SecretsVault(Path("/app/data"))
    vault.save_secret("bitget_api_key", "my-secret-key")
    key = vault.get_secret("bitget_api_key")
"""
import os
import json
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SecretMetadata(BaseModel):
    """Metadata stored with secrets."""
    created_at: str
    updated_at: str
    version: int = 1


class SecretsVault:
    """
    Secure secrets storage with Fernet (AES-256) encryption.
    
    Usage:
        vault = SecretsVault(Path("/app/data"))
        vault.save_secret("bitget_api_key", "my-secret-key")
        key = vault.get_secret("bitget_api_key")
    """
    
    def __init__(self, data_dir: Path):
        """
        Initialize the secrets vault.
        
        Args:
            data_dir: Directory for storing encrypted secrets.
                      Must be on a persistent volume in Docker.
        """
        self.data_dir = Path(data_dir)
        self.key_file = self.data_dir / ".key"
        self.secrets_file = self.data_dir / ".secrets.enc"
        self.metadata_file = self.data_dir / ".secrets.meta"
        
        # Ensure directory exists with proper permissions
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize encryption
        self._fernet = self._load_or_create_key()
    
    def _load_or_create_key(self) -> Fernet:
        """Load existing key or generate a new one."""
        if self.key_file.exists():
            key = self.key_file.read_bytes()
            # Validate key format
            try:
                return Fernet(key)
            except Exception:
                # Key is corrupted, regenerate
                logger.warning("Encryption key corrupted, generating new one")
                return self._generate_new_key()
        else:
            return self._generate_new_key()
    
    def _generate_new_key(self) -> Fernet:
        """Generate a new encryption key."""
        key = Fernet.generate_key()
        
        # Write atomically with secure permissions
        temp_fd, temp_path = tempfile.mkstemp(dir=self.data_dir)
        try:
            os.write(temp_fd, key)
            os.close(temp_fd)
            os.chmod(temp_path, 0o600)  # Owner read/write only
            shutil.move(temp_path, self.key_file)
            logger.info("Generated new encryption key")
        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
        
        return Fernet(key)
    
    def _load_secrets(self) -> Dict[str, str]:
        """Load and decrypt secrets from file."""
        if not self.secrets_file.exists():
            return {}
        
        try:
            encrypted = self.secrets_file.read_bytes()
            decrypted = self._fernet.decrypt(encrypted)
            return json.loads(decrypted.decode('utf-8'))
        except InvalidToken:
            logger.warning("Failed to decrypt secrets (key mismatch)")
            return {}
        except json.JSONDecodeError:
            logger.warning("Corrupted secrets file")
            return {}
        except Exception as e:
            logger.warning(f"Error loading secrets: {type(e).__name__}")
            return {}
    
    def _save_secrets(self, secrets: Dict[str, str]) -> None:
        """Encrypt and save secrets to file."""
        # Serialize and encrypt
        data = json.dumps(secrets).encode('utf-8')
        encrypted = self._fernet.encrypt(data)
        
        # Write atomically
        temp_fd, temp_path = tempfile.mkstemp(dir=self.data_dir)
        try:
            os.write(temp_fd, encrypted)
            os.close(temp_fd)
            os.chmod(temp_path, 0o600)
            shutil.move(temp_path, self.secrets_file)
            
            # Update metadata
            self._save_metadata()
        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
    
    def _save_metadata(self) -> None:
        """Save secrets metadata."""
        now = datetime.now().isoformat()
        
        # Load existing metadata to preserve created_at
        created_at = now
        version = 1
        if self.metadata_file.exists():
            try:
                existing = json.loads(self.metadata_file.read_text())
                created_at = existing.get('created_at', now)
                version = existing.get('version', 0) + 1
            except (json.JSONDecodeError, IOError):
                pass
        
        meta = SecretMetadata(
            created_at=created_at,
            updated_at=now,
            version=version,
        )
        self.metadata_file.write_text(meta.model_dump_json())
    
    def save_secret(self, key: str, value: str) -> None:
        """
        Save an encrypted secret.
        
        Args:
            key: Secret identifier (e.g., 'bitget_api_key')
            value: Secret value (will be encrypted)
        """
        secrets = self._load_secrets()
        secrets[key] = value
        self._save_secrets(secrets)
        logger.info(f"Saved secret: {key}")
    
    def save_secrets(self, secrets_dict: Dict[str, str]) -> None:
        """
        Save multiple secrets at once.
        
        Args:
            secrets_dict: Dictionary of key-value pairs
        """
        secrets = self._load_secrets()
        secrets.update(secrets_dict)
        self._save_secrets(secrets)
        logger.info(f"Saved {len(secrets_dict)} secrets")
    
    def get_secret(self, key: str) -> Optional[str]:
        """
        Retrieve a decrypted secret.
        
        Args:
            key: Secret identifier
            
        Returns:
            Decrypted secret value, or None if not found
        """
        secrets = self._load_secrets()
        return secrets.get(key)
    
    def delete_secret(self, key: str) -> bool:
        """
        Delete a secret.
        
        Args:
            key: Secret identifier
            
        Returns:
            True if secret was deleted, False if not found
        """
        secrets = self._load_secrets()
        if key in secrets:
            del secrets[key]
            self._save_secrets(secrets)
            logger.info(f"Deleted secret: {key}")
            return True
        return False
    
    def list_secrets(self) -> List[str]:
        """
        List all secret keys (not values).
        
        Returns:
            List of secret identifiers
        """
        secrets = self._load_secrets()
        return list(secrets.keys())
    
    def has_secret(self, key: str) -> bool:
        """Check if a secret exists."""
        secrets = self._load_secrets()
        return key in secrets
    
    def clear_all(self) -> None:
        """Delete all secrets (dangerous!)."""
        self._save_secrets({})
        logger.warning("Cleared all secrets")
    
    def rotate_key(self) -> None:
        """
        Rotate the encryption key.
        
        This decrypts all secrets with the old key and re-encrypts
        with a new key. Should be called periodically for security.
        """
        # Load secrets with old key
        secrets = self._load_secrets()
        
        # Generate new key
        self._fernet = self._generate_new_key()
        
        # Re-encrypt with new key
        self._save_secrets(secrets)
        logger.info("Rotated encryption key")
    
    def get_status(self) -> Dict[str, Any]:
        """Get vault status information (no secrets exposed)."""
        return {
            "initialized": self.key_file.exists(),
            "has_secrets": self.secrets_file.exists(),
            "secret_count": len(self.list_secrets()),
            "secrets_configured": {
                "bitget": all([
                    self.has_secret("bitget_api_key"),
                    self.has_secret("bitget_api_secret"),
                    self.has_secret("bitget_passphrase"),
                ]),
                "azure_openai": self.has_secret("azure_openai_api_key"),
            }
        }
    
    def get_masked_secret(self, key: str, visible_chars: int = 4) -> Optional[str]:
        """
        Get a masked version of a secret for display.
        
        Args:
            key: Secret identifier
            visible_chars: Number of characters to show at start/end
            
        Returns:
            Masked secret (e.g., "sk-12****89") or None if not found
        """
        value = self.get_secret(key)
        if not value:
            return None
        
        if len(value) <= visible_chars * 2:
            return "*" * len(value)
        
        return f"{value[:visible_chars]}****{value[-visible_chars:]}"
    
    # =========================================================================
    # User-Scoped Secrets (Multi-User Support)
    # =========================================================================
    
    def _user_key(self, user_id: str, key: str) -> str:
        """
        Generate a namespaced key for user-specific secrets.
        
        Format: user_{user_id}_{key}
        
        Args:
            user_id: User's unique identifier
            key: Secret key name
            
        Returns:
            Namespaced key string
        """
        # Sanitize user_id to prevent key injection
        safe_user_id = user_id.replace("_", "-")
        return f"user_{safe_user_id}_{key}"
    
    def save_user_secret(self, user_id: str, key: str, value: str) -> None:
        """
        Save an encrypted secret for a specific user.
        
        Args:
            user_id: User's unique identifier
            key: Secret identifier (e.g., 'bitget_api_key')
            value: Secret value (will be encrypted)
        """
        namespaced_key = self._user_key(user_id, key)
        self.save_secret(namespaced_key, value)
        logger.info(f"Saved user secret: {key} for user {user_id[:8]}...")
    
    def save_user_secrets(self, user_id: str, secrets_dict: Dict[str, str]) -> None:
        """
        Save multiple secrets for a user at once.
        
        Args:
            user_id: User's unique identifier
            secrets_dict: Dictionary of key-value pairs
        """
        namespaced = {
            self._user_key(user_id, k): v 
            for k, v in secrets_dict.items()
        }
        self.save_secrets(namespaced)
        logger.info(f"Saved {len(secrets_dict)} user secrets for user {user_id[:8]}...")
    
    def get_user_secret(self, user_id: str, key: str) -> Optional[str]:
        """
        Retrieve a decrypted secret for a specific user.
        
        Args:
            user_id: User's unique identifier
            key: Secret identifier
            
        Returns:
            Decrypted secret value, or None if not found
        """
        namespaced_key = self._user_key(user_id, key)
        return self.get_secret(namespaced_key)
    
    def delete_user_secret(self, user_id: str, key: str) -> bool:
        """
        Delete a user's secret.
        
        Args:
            user_id: User's unique identifier
            key: Secret identifier
            
        Returns:
            True if secret was deleted, False if not found
        """
        namespaced_key = self._user_key(user_id, key)
        result = self.delete_secret(namespaced_key)
        if result:
            logger.info(f"Deleted user secret: {key} for user {user_id[:8]}...")
        return result
    
    def list_user_secrets(self, user_id: str) -> List[str]:
        """
        List all secret keys for a specific user.
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            List of secret identifiers (without the user_ prefix)
        """
        prefix = self._user_key(user_id, "")
        all_keys = self.list_secrets()
        user_keys = [
            k[len(prefix):] for k in all_keys 
            if k.startswith(prefix)
        ]
        return user_keys
    
    def has_user_secret(self, user_id: str, key: str) -> bool:
        """Check if a user has a specific secret."""
        namespaced_key = self._user_key(user_id, key)
        return self.has_secret(namespaced_key)
    
    def get_masked_user_secret(
        self, 
        user_id: str, 
        key: str, 
        visible_chars: int = 4
    ) -> Optional[str]:
        """
        Get a masked version of a user's secret for display.
        
        Args:
            user_id: User's unique identifier
            key: Secret identifier
            visible_chars: Number of characters to show at start/end
            
        Returns:
            Masked secret or None if not found
        """
        namespaced_key = self._user_key(user_id, key)
        return self.get_masked_secret(namespaced_key, visible_chars)
    
    def delete_all_user_secrets(self, user_id: str) -> int:
        """
        Delete all secrets for a specific user.
        
        Useful when deleting a user account.
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            Number of secrets deleted
        """
        user_keys = self.list_user_secrets(user_id)
        count = 0
        for key in user_keys:
            if self.delete_user_secret(user_id, key):
                count += 1
        logger.info(f"Deleted {count} secrets for user {user_id[:8]}...")
        return count
    
    def get_user_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get vault status for a specific user.
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            Status dictionary with secret configuration info
        """
        return {
            "secret_count": len(self.list_user_secrets(user_id)),
            "secrets_configured": {
                "bitget": all([
                    self.has_user_secret(user_id, "bitget_api_key"),
                    self.has_user_secret(user_id, "bitget_api_secret"),
                    self.has_user_secret(user_id, "bitget_passphrase"),
                ]),
                "azure_openai": self.has_user_secret(user_id, "azure_openai_api_key"),
            }
        }


# ============================================================================
# FastAPI Dependency
# ============================================================================

_vault_instance: Optional[SecretsVault] = None


def get_vault() -> SecretsVault:
    """Get the secrets vault instance (FastAPI dependency)."""
    global _vault_instance
    if _vault_instance is None:
        from app.core.config import get_settings
        settings = get_settings()
        _vault_instance = SecretsVault(Path(settings.secrets_dir))
    return _vault_instance


def reset_vault() -> None:
    """Reset the vault instance (for testing)."""
    global _vault_instance
    _vault_instance = None
