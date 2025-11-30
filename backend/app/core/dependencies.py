"""
FastAPI dependencies for dependency injection.
"""
from functools import lru_cache
from typing import Generator

from app.core.config import Settings, get_settings


def get_settings_dependency() -> Settings:
    """Dependency to inject settings."""
    return get_settings()


# Placeholder for future dependencies
# These will be added as we implement services

# @lru_cache()
# def get_agent_service():
#     """Get cached agent service instance."""
#     from app.services.agent_service import AgentService
#     return AgentService()

# @lru_cache()
# def get_secrets_vault():
#     """Get cached secrets vault instance."""
#     from app.core.security import SecretsVault
#     settings = get_settings()
#     return SecretsVault(settings.secrets_dir)
