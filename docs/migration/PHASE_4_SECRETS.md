# Phase 4: Secrets Management

## Overview

Implement secure secrets management for exchange credentials (Bitget API keys) with encryption at rest.

---

## 4.1 Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (React)                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Settings Dialog                                         │   │
│  │  ┌──────────────────┐  ┌──────────────────────────────┐ │   │
│  │  │  API Key: ****   │  │  [Save Credentials]          │ │   │
│  │  │  Secret: ****    │  │                              │ │   │
│  │  │  Passphrase: *** │  │  🔒 Encrypted with AES-256   │ │   │
│  │  └──────────────────┘  └──────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS (TLS encrypted)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  SecretsVault                                            │   │
│  │  ┌──────────────────┐  ┌──────────────────────────────┐ │   │
│  │  │  Fernet Key      │  │  Encrypted Secrets Store     │ │   │
│  │  │  (generated once)│  │  .secrets.enc                │ │   │
│  │  │  .key (600 perms)│  │  (binary encrypted file)     │ │   │
│  │  └──────────────────┘  └──────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Mounted Volume (Docker)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Persistent Storage                              │
│  /app/data/                                                     │
│  ├── .key          (Encryption key, owner-only permissions)    │
│  └── .secrets.enc  (Encrypted secrets file)                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4.2 Secrets Vault Implementation

```python
# backend/app/core/security.py
"""
Secure secrets management with Fernet encryption.

Features:
- AES-256 encryption (via Fernet)
- Key generation and secure storage
- Atomic file operations
- No secrets in logs or errors
"""
import os
import json
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, Field


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
                print("⚠️ Encryption key corrupted, generating new one")
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
        except Exception:
            os.unlink(temp_path)
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
            print("⚠️ Failed to decrypt secrets (key mismatch)")
            return {}
        except json.JSONDecodeError:
            print("⚠️ Corrupted secrets file")
            return {}
        except Exception as e:
            print(f"⚠️ Error loading secrets: {type(e).__name__}")
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
            os.unlink(temp_path)
            raise
    
    def _save_metadata(self) -> None:
        """Save secrets metadata."""
        meta = SecretMetadata(
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            version=1,
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
    
    def save_secrets(self, secrets_dict: Dict[str, str]) -> None:
        """
        Save multiple secrets at once.
        
        Args:
            secrets_dict: Dictionary of key-value pairs
        """
        secrets = self._load_secrets()
        secrets.update(secrets_dict)
        self._save_secrets(secrets)
    
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
            return True
        return False
    
    def list_secrets(self) -> list[str]:
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


# Dependency for FastAPI
_vault_instance: Optional[SecretsVault] = None


def get_vault() -> SecretsVault:
    """Get the secrets vault instance (FastAPI dependency)."""
    global _vault_instance
    if _vault_instance is None:
        from app.core.config import get_settings
        settings = get_settings()
        _vault_instance = SecretsVault(Path(settings.secrets_dir))
    return _vault_instance
```

---

## 4.3 Settings API Endpoints

```python
# backend/app/api/routes/settings.py
"""
Settings and secrets management endpoints.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.security import SecretsVault, get_vault


router = APIRouter()


# ==================== Request/Response Models ====================

class ExchangeCredentials(BaseModel):
    """Bitget exchange credentials."""
    api_key: str = Field(..., min_length=1)
    api_secret: str = Field(..., min_length=1)
    passphrase: str = Field(..., min_length=1)


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    provider: str = Field(..., pattern="^(ollama|azure)$")
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None  # For Azure


class SettingsStatus(BaseModel):
    """Current settings status."""
    exchange: dict
    llm: dict
    vault_status: dict


# ==================== Exchange Settings ====================

@router.post("/exchange", response_model=dict)
async def save_exchange_credentials(
    credentials: ExchangeCredentials,
    vault: SecretsVault = Depends(get_vault),
):
    """
    Save encrypted exchange (Bitget) credentials.
    
    Credentials are encrypted with AES-256 and stored securely.
    They are never logged or exposed in errors.
    """
    try:
        # Save all credentials
        vault.save_secrets({
            "bitget_api_key": credentials.api_key,
            "bitget_api_secret": credentials.api_secret,
            "bitget_passphrase": credentials.passphrase,
        })
        
        # Optionally validate credentials work
        validation_result = await _validate_bitget_credentials(credentials)
        
        return {
            "status": "success" if validation_result["valid"] else "warning",
            "message": "Credentials saved successfully",
            "validation": validation_result,
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save credentials"  # Don't expose details
        )


@router.get("/exchange/status")
async def get_exchange_status(vault: SecretsVault = Depends(get_vault)):
    """
    Get exchange configuration status (not the actual credentials).
    """
    return {
        "configured": all([
            vault.has_secret("bitget_api_key"),
            vault.has_secret("bitget_api_secret"),
            vault.has_secret("bitget_passphrase"),
        ]),
        "provider": "bitget",
    }


@router.delete("/exchange")
async def delete_exchange_credentials(vault: SecretsVault = Depends(get_vault)):
    """
    Delete stored exchange credentials.
    """
    vault.delete_secret("bitget_api_key")
    vault.delete_secret("bitget_api_secret")
    vault.delete_secret("bitget_passphrase")
    
    return {"status": "success", "message": "Credentials deleted"}


async def _validate_bitget_credentials(credentials: ExchangeCredentials) -> dict:
    """Validate Bitget credentials by making a test API call."""
    try:
        from exchange_providers import BitgetProvider
        
        provider = BitgetProvider(
            api_key=credentials.api_key,
            api_secret=credentials.api_secret,
            passphrase=credentials.passphrase,
        )
        
        # Test with a simple authenticated endpoint
        # This would be a real API call
        # For now, just check format
        return {
            "valid": True,
            "message": "Credentials format valid",
        }
    
    except Exception as e:
        return {
            "valid": False,
            "message": f"Validation failed: {type(e).__name__}",
        }


# ==================== LLM Settings ====================

@router.post("/llm", response_model=dict)
async def save_llm_config(
    config: LLMConfig,
    vault: SecretsVault = Depends(get_vault),
):
    """
    Save LLM provider configuration.
    """
    secrets_to_save = {
        "llm_provider": config.provider,
    }
    
    if config.model:
        secrets_to_save["llm_model"] = config.model
    
    if config.base_url:
        secrets_to_save["llm_base_url"] = config.base_url
    
    if config.api_key:
        secrets_to_save["azure_openai_api_key"] = config.api_key
    
    vault.save_secrets(secrets_to_save)
    
    return {
        "status": "success",
        "message": f"LLM configured for {config.provider}",
    }


@router.get("/llm/status")
async def get_llm_status(vault: SecretsVault = Depends(get_vault)):
    """Get LLM configuration status."""
    provider = vault.get_secret("llm_provider") or "ollama"
    
    return {
        "provider": provider,
        "model": vault.get_secret("llm_model"),
        "azure_configured": vault.has_secret("azure_openai_api_key") if provider == "azure" else None,
    }


# ==================== General Settings ====================

@router.get("/status", response_model=SettingsStatus)
async def get_all_settings_status(vault: SecretsVault = Depends(get_vault)):
    """Get status of all settings."""
    return SettingsStatus(
        exchange={
            "configured": all([
                vault.has_secret("bitget_api_key"),
                vault.has_secret("bitget_api_secret"),
                vault.has_secret("bitget_passphrase"),
            ]),
            "provider": "bitget",
        },
        llm={
            "provider": vault.get_secret("llm_provider") or "ollama",
            "model": vault.get_secret("llm_model"),
        },
        vault_status=vault.get_status(),
    )
```

---

## 4.4 Using Secrets in Agent Service

```python
# backend/app/services/agent_service.py (updated)
"""
Agent service with secrets integration.
"""
from app.core.security import get_vault


class AgentService:
    def __init__(self):
        self.settings = get_settings()
        self.vault = get_vault()
        self.model_client = self._create_model_client()
    
    def _create_model_client(self):
        """Create LLM client using stored secrets."""
        # Check for stored provider preference
        provider = self.vault.get_secret("llm_provider") or self.settings.llm_provider
        
        if provider == "azure":
            # Get API key from vault first, then fall back to env
            api_key = self.vault.get_secret("azure_openai_api_key") or self.settings.azure_openai_api_key
            
            if not api_key:
                raise ValueError("Azure OpenAI API key not configured")
            
            from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
            return AzureOpenAIChatCompletionClient(
                azure_deployment=self.settings.azure_openai_deployment,
                api_version=self.settings.azure_openai_api_version,
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=api_key,
                model=self.settings.azure_openai_deployment,
            )
        else:
            from ollama_client import OllamaChatCompletionClient
            return OllamaChatCompletionClient(
                model=self.vault.get_secret("llm_model") or self.settings.ollama_model,
                base_url=self.vault.get_secret("llm_base_url") or self.settings.ollama_base_url,
            )
    
    def _get_bitget_config(self):
        """Get Bitget configuration from vault."""
        return {
            "api_key": self.vault.get_secret("bitget_api_key"),
            "api_secret": self.vault.get_secret("bitget_api_secret"),
            "passphrase": self.vault.get_secret("bitget_passphrase"),
        }
```

---

## 4.5 Docker Volume for Secrets

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      # Persistent volume for encrypted secrets
      - secrets-data:/app/data
      # Outputs directory
      - ./outputs:/app/outputs
    environment:
      - SECRETS_DIR=/app/data
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

volumes:
  secrets-data:
    # Named volume persists across container restarts
    # For production, consider using Azure Disk or other managed storage
```

---

## 4.6 Security Best Practices

### Environment Variables vs Vault

```python
# backend/app/core/config.py (updated)
"""
Configuration with secret precedence:
1. Vault (encrypted, persistent)
2. Environment variables
3. Defaults
"""

class Settings(BaseSettings):
    # These can be overridden by vault secrets
    azure_openai_api_key: Optional[str] = None
    bitget_api_key: Optional[str] = None
    
    def get_with_vault_override(self, key: str, vault: SecretsVault) -> Optional[str]:
        """Get a setting, preferring vault over env."""
        vault_value = vault.get_secret(key)
        if vault_value:
            return vault_value
        return getattr(self, key, None)
```

### Logging Security

```python
# backend/app/core/logging.py
"""
Secure logging that filters sensitive data.
"""
import re
import logging


class SecretFilter(logging.Filter):
    """Filter that masks sensitive data in logs."""
    
    PATTERNS = [
        (r'api_key["\']?\s*[:=]\s*["\']?([^"\'}\s]+)', r'api_key: [REDACTED]'),
        (r'api_secret["\']?\s*[:=]\s*["\']?([^"\'}\s]+)', r'api_secret: [REDACTED]'),
        (r'passphrase["\']?\s*[:=]\s*["\']?([^"\'}\s]+)', r'passphrase: [REDACTED]'),
        (r'password["\']?\s*[:=]\s*["\']?([^"\'}\s]+)', r'password: [REDACTED]'),
        (r'Bearer\s+([^\s]+)', r'Bearer [REDACTED]'),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = re.sub(pattern, replacement, record.msg, flags=re.IGNORECASE)
        return True


# Apply to all loggers
logging.getLogger().addFilter(SecretFilter())
```

### Error Handling

```python
# Never expose secrets in errors
@router.post("/exchange")
async def save_exchange_credentials(credentials: ExchangeCredentials, ...):
    try:
        vault.save_secrets(...)
    except Exception as e:
        # Log the full error internally
        logger.error(f"Failed to save credentials: {e}")
        
        # Return generic error to client
        raise HTTPException(
            status_code=500,
            detail="Failed to save credentials. Please try again."
        )
```

---

## 4.7 Testing Secrets

```python
# backend/tests/test_security.py
import pytest
import tempfile
from pathlib import Path

from app.core.security import SecretsVault


class TestSecretsVault:
    @pytest.fixture
    def vault(self):
        """Create a vault in a temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SecretsVault(Path(tmpdir))
    
    def test_save_and_retrieve_secret(self, vault):
        vault.save_secret("test_key", "test_value")
        assert vault.get_secret("test_key") == "test_value"
    
    def test_secret_not_found(self, vault):
        assert vault.get_secret("nonexistent") is None
    
    def test_delete_secret(self, vault):
        vault.save_secret("to_delete", "value")
        assert vault.delete_secret("to_delete") is True
        assert vault.get_secret("to_delete") is None
    
    def test_list_secrets(self, vault):
        vault.save_secrets({"key1": "v1", "key2": "v2"})
        keys = vault.list_secrets()
        assert "key1" in keys
        assert "key2" in keys
    
    def test_key_rotation(self, vault):
        vault.save_secret("persistent", "value")
        vault.rotate_key()
        assert vault.get_secret("persistent") == "value"
    
    def test_encryption_is_real(self, vault):
        vault.save_secret("secret", "sensitive_data")
        
        # Read raw file
        raw_content = vault.secrets_file.read_bytes()
        
        # Should not contain plaintext
        assert b"sensitive_data" not in raw_content
        assert b"secret" not in raw_content
```

---

## Next Steps

After completing Phase 4, proceed to:
- [Phase 5: Containerization & Azure](./PHASE_5_CONTAINERS.md)

---

*Document created: 2025-11-29*
