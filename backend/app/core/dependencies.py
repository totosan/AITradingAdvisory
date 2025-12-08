"""
FastAPI dependencies for dependency injection.
"""
from functools import lru_cache
from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.auth import decode_access_token
from app.core.repositories import UserRepository
from app.models.database import User


# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


def get_settings_dependency() -> Settings:
    """Dependency to inject settings."""
    return get_settings()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency to get the currently authenticated user.
    
    Extracts the JWT token from the Authorization header,
    validates it, and returns the corresponding user.
    
    Usage in routes:
        @router.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.id}
    
    Raises:
        HTTPException 401: If token is missing or invalid
        HTTPException 401: If user not found or inactive
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    token_data = decode_access_token(token)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    repo = UserRepository(db)
    user = await repo.get_by_id(token_data.user_id)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Optional user authentication dependency.
    
    Returns the user if authenticated, None otherwise.
    Useful for routes that work for both authenticated and anonymous users.
    
    Usage:
        @router.get("/public-or-private")
        async def mixed_route(user: Optional[User] = Depends(get_current_user_optional)):
            if user:
                return {"message": f"Hello, {user.email}"}
            return {"message": "Hello, anonymous"}
    """
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def get_current_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to ensure the current user is an admin.
    
    Usage:
        @router.delete("/admin-only")
        async def admin_route(user: User = Depends(get_current_admin_user)):
            ...
    
    Raises:
        HTTPException 403: If user is not an admin
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user


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
