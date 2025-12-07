"""
Settings and secrets management endpoints.

Provides API for managing:
- Exchange credentials (Bitget)
- LLM configuration (Azure OpenAI / Ollama)

All secrets are encrypted at rest using Fernet (AES-256).
"""
from typing import Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.security import SecretsVault, get_vault
from app.core.config import get_settings

# Import exchange tools reset function
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))
try:
    from exchange_tools import reset_exchange_manager, set_vault
except ImportError:
    reset_exchange_manager = None
    set_vault = None


router = APIRouter(prefix="/settings", tags=["settings"])


# ============================================================================
# Azure OpenAI API Version Mapping
# ============================================================================
# Based on Microsoft documentation:
# - Structured outputs (json_schema) require API version >= 2024-08-01-preview
# - GA API with structured outputs: 2024-10-21
# - Latest preview: 2024-12-01-preview

# Models that support structured outputs and their recommended API versions
MODEL_API_VERSIONS: Dict[str, str] = {
    # GPT-4o models - all support structured outputs
    "gpt-4o": "2024-10-21",
    "gpt-4o-mini": "2024-10-21",
    "gpt-4o-audio-preview": "2024-10-21",
    
    # GPT-4.1 series
    "gpt-4.1": "2024-10-21",
    "gpt-4.1-mini": "2024-10-21",
    "gpt-4.1-nano": "2024-10-21",
    
    # GPT-4.5 preview
    "gpt-4.5-preview": "2024-10-21",
    
    # O-series (reasoning models)
    "o1": "2024-10-21",
    "o1-preview": "2024-10-21",
    "o1-mini": "2024-10-21",
    "o3": "2024-10-21",
    "o3-mini": "2024-10-21",
    "o3-pro": "2024-10-21",
    "o4-mini": "2024-10-21",
    
    # Legacy models - older API version is fine
    "gpt-4": "2024-02-15-preview",
    "gpt-4-turbo": "2024-02-15-preview",
    "gpt-4-32k": "2024-02-15-preview",
    "gpt-35-turbo": "2024-02-15-preview",
    "gpt-35-turbo-16k": "2024-02-15-preview",
}

# Default API version for unknown models (use GA with structured outputs support)
DEFAULT_API_VERSION = "2024-10-21"


def get_recommended_api_version(model: Optional[str]) -> str:
    """
    Get the recommended API version for a given model.
    
    Args:
        model: The model/deployment name (e.g., "gpt-4o", "gpt-4")
        
    Returns:
        Recommended API version string
    """
    if not model:
        return DEFAULT_API_VERSION
    
    # Normalize model name (lowercase, handle deployment naming variations)
    model_lower = model.lower().strip()
    
    # Check exact match first
    if model_lower in MODEL_API_VERSIONS:
        return MODEL_API_VERSIONS[model_lower]
    
    # Check for partial matches (e.g., "gpt-4o-2024-08-06" -> "gpt-4o")
    for model_prefix, api_version in MODEL_API_VERSIONS.items():
        if model_lower.startswith(model_prefix):
            return api_version
    
    # For unknown models, use latest GA with structured outputs
    return DEFAULT_API_VERSION

# ============================================================================
# Request/Response Models
# ============================================================================

class ExchangeCredentials(BaseModel):
    """Bitget exchange credentials."""
    api_key: str = Field(..., min_length=1, description="Bitget API key")
    api_secret: str = Field(..., min_length=1, description="Bitget API secret")
    passphrase: str = Field(..., min_length=1, description="Bitget passphrase")


class ExchangeStatus(BaseModel):
    """Exchange configuration status."""
    configured: bool
    provider: str = "bitget"
    api_key_masked: Optional[str] = None


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    provider: str = Field(..., pattern="^(ollama|azure)$", description="LLM provider: 'ollama' or 'azure'")
    model: Optional[str] = Field(None, description="Model name/deployment")
    base_url: Optional[str] = Field(None, description="Base URL for Ollama")
    api_key: Optional[str] = Field(None, description="API key for Azure OpenAI")
    endpoint: Optional[str] = Field(None, description="Azure OpenAI endpoint URL")
    api_version: Optional[str] = Field(None, description="Azure OpenAI API version (e.g., 2024-10-21). Leave empty for auto-detection based on model.")


class LLMStatus(BaseModel):
    """LLM configuration status."""
    provider: str
    model: Optional[str] = None
    azure_configured: Optional[bool] = None
    endpoint_masked: Optional[str] = None
    api_version: Optional[str] = None
    api_version_auto: bool = False  # True if version was auto-detected


class SettingsStatus(BaseModel):
    """Current settings status."""
    exchange: ExchangeStatus
    llm: LLMStatus
    vault_status: dict


class OperationResult(BaseModel):
    """Generic operation result."""
    status: str
    message: str
    validation: Optional[dict] = None


# ============================================================================
# Exchange Settings Endpoints
# ============================================================================

@router.post("/exchange", response_model=OperationResult)
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
        
        # Reset exchange manager to reload with new credentials
        if reset_exchange_manager is not None:
            reset_exchange_manager()
        
        # Optionally validate credentials work
        validation_result = await _validate_bitget_credentials(credentials)
        
        return OperationResult(
            status="success" if validation_result["valid"] else "warning",
            message="Credentials saved and exchange manager reloaded",
            validation=validation_result,
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save credentials"  # Don't expose details
        )


@router.get("/exchange", response_model=ExchangeStatus)
async def get_exchange_status(vault: SecretsVault = Depends(get_vault)):
    """
    Get exchange configuration status (not the actual credentials).
    """
    configured = all([
        vault.has_secret("bitget_api_key"),
        vault.has_secret("bitget_api_secret"),
        vault.has_secret("bitget_passphrase"),
    ])
    
    return ExchangeStatus(
        configured=configured,
        provider="bitget",
        api_key_masked=vault.get_masked_secret("bitget_api_key") if configured else None,
    )


@router.delete("/exchange", response_model=OperationResult)
async def delete_exchange_credentials(vault: SecretsVault = Depends(get_vault)):
    """
    Delete stored exchange credentials.
    """
    vault.delete_secret("bitget_api_key")
    vault.delete_secret("bitget_api_secret")
    vault.delete_secret("bitget_passphrase")
    
    # Reset exchange manager to use env vars or no auth
    if reset_exchange_manager is not None:
        reset_exchange_manager()
    
    return OperationResult(
        status="success",
        message="Exchange credentials deleted"
    )


async def _validate_bitget_credentials(credentials: ExchangeCredentials) -> dict:
    """Validate Bitget credentials by checking format."""
    try:
        # Basic validation - check format
        if len(credentials.api_key) < 10:
            return {"valid": False, "message": "API key too short"}
        if len(credentials.api_secret) < 10:
            return {"valid": False, "message": "API secret too short"}
        if len(credentials.passphrase) < 4:
            return {"valid": False, "message": "Passphrase too short"}
        
        # TODO: Add actual API validation call when needed
        return {
            "valid": True,
            "message": "Credentials format valid",
        }
    
    except Exception as e:
        return {
            "valid": False,
            "message": f"Validation failed: {type(e).__name__}",
        }


# ============================================================================
# LLM Settings Endpoints
# ============================================================================

@router.post("/llm", response_model=OperationResult)
async def save_llm_config(
    config: LLMConfig,
    vault: SecretsVault = Depends(get_vault),
):
    """
    Save LLM provider configuration.
    
    If api_version is not provided, it will be auto-detected based on the model.
    """
    try:
        secrets_to_save = {
            "llm_provider": config.provider,
        }
        
        if config.model:
            secrets_to_save["llm_model"] = config.model
            secrets_to_save["azure_openai_deployment"] = config.model
        
        if config.base_url:
            secrets_to_save["llm_base_url"] = config.base_url
        
        if config.api_key:
            secrets_to_save["azure_openai_api_key"] = config.api_key
        
        if config.endpoint:
            secrets_to_save["azure_openai_endpoint"] = config.endpoint
        
        # Handle API version: use provided value or auto-detect
        api_version_message = ""
        if config.api_version:
            secrets_to_save["azure_openai_api_version"] = config.api_version
            secrets_to_save["azure_openai_api_version_auto"] = "false"
            api_version_message = f" (API version: {config.api_version})"
        elif config.model and config.provider == "azure":
            # Auto-detect API version based on model
            auto_version = get_recommended_api_version(config.model)
            secrets_to_save["azure_openai_api_version"] = auto_version
            secrets_to_save["azure_openai_api_version_auto"] = "true"
            api_version_message = f" (API version auto-detected: {auto_version})"
        
        vault.save_secrets(secrets_to_save)
        
        # Reset model client in agent service to use new credentials
        # This is done by resetting the global agent service instance
        from app.api.websocket.stream import reset_agent_service
        try:
            reset_agent_service()
        except Exception:
            pass  # Agent service may not be initialized yet
        
        return OperationResult(
            status="success",
            message=f"LLM configured for {config.provider}{api_version_message}",
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save LLM configuration"
        )


@router.get("/llm", response_model=LLMStatus)
async def get_llm_status(vault: SecretsVault = Depends(get_vault)):
    """Get LLM configuration status."""
    settings = get_settings()
    
    # Check vault first, then fall back to env config
    provider = vault.get_secret("llm_provider") or settings.llm_provider
    model = vault.get_secret("llm_model")
    api_version = vault.get_secret("azure_openai_api_version")
    api_version_auto = vault.get_secret("azure_openai_api_version_auto") == "true"
    
    if provider == "azure":
        model = model or settings.azure_openai_deployment
        azure_configured = vault.has_secret("azure_openai_api_key") or bool(settings.azure_openai_api_key)
        endpoint = vault.get_secret("azure_openai_endpoint") or settings.azure_openai_endpoint
        endpoint_masked = f"{endpoint[:30]}..." if endpoint and len(endpoint) > 30 else endpoint
        
        # If no API version stored, auto-detect based on model
        if not api_version:
            api_version = get_recommended_api_version(model)
            api_version_auto = True
    else:
        model = model or settings.ollama_model
        azure_configured = None
        endpoint_masked = None
        api_version = None
        api_version_auto = False
    
    return LLMStatus(
        provider=provider,
        model=model,
        azure_configured=azure_configured,
        endpoint_masked=endpoint_masked,
        api_version=api_version,
        api_version_auto=api_version_auto,
    )


@router.delete("/llm", response_model=OperationResult)
async def delete_llm_config(vault: SecretsVault = Depends(get_vault)):
    """
    Delete stored LLM configuration (reverts to .env settings).
    """
    vault.delete_secret("llm_provider")
    vault.delete_secret("llm_model")
    vault.delete_secret("llm_base_url")
    vault.delete_secret("azure_openai_api_key")
    vault.delete_secret("azure_openai_endpoint")
    vault.delete_secret("azure_openai_deployment")
    vault.delete_secret("azure_openai_api_version")
    
    return OperationResult(
        status="success",
        message="LLM configuration deleted, using environment settings"
    )


# ============================================================================
# General Settings Endpoints
# ============================================================================

@router.get("/status", response_model=SettingsStatus)
async def get_all_settings_status(vault: SecretsVault = Depends(get_vault)):
    """Get status of all settings."""
    settings = get_settings()
    
    # Exchange status
    exchange_configured = all([
        vault.has_secret("bitget_api_key"),
        vault.has_secret("bitget_api_secret"),
        vault.has_secret("bitget_passphrase"),
    ])
    
    # LLM status
    provider = vault.get_secret("llm_provider") or settings.llm_provider
    model = vault.get_secret("llm_model")
    api_version = vault.get_secret("azure_openai_api_version") or settings.azure_openai_api_version
    endpoint = vault.get_secret("azure_openai_endpoint") or settings.azure_openai_endpoint
    endpoint_masked = f"{endpoint[:30]}..." if endpoint and len(endpoint) > 30 else endpoint
    
    if provider == "azure":
        model = model or settings.azure_openai_deployment
        azure_configured = vault.has_secret("azure_openai_api_key") or bool(settings.azure_openai_api_key)
    else:
        model = model or settings.ollama_model
        azure_configured = None
        api_version = None
        endpoint_masked = None
    
    return SettingsStatus(
        exchange=ExchangeStatus(
            configured=exchange_configured,
            provider="bitget",
            api_key_masked=vault.get_masked_secret("bitget_api_key") if exchange_configured else None,
        ),
        llm=LLMStatus(
            provider=provider,
            model=model,
            azure_configured=azure_configured,
            endpoint_masked=endpoint_masked,
            api_version=api_version,
        ),
        vault_status=vault.get_status(),
    )


@router.post("/vault/rotate-key", response_model=OperationResult)
async def rotate_vault_key(vault: SecretsVault = Depends(get_vault)):
    """
    Rotate the encryption key.
    
    This re-encrypts all secrets with a new key. Should be done periodically.
    """
    try:
        vault.rotate_key()
        return OperationResult(
            status="success",
            message="Encryption key rotated successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate encryption key"
        )
