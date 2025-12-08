"""
Authentication API routes.

Endpoints:
- POST /api/v1/auth/register - Register new user
- POST /api/v1/auth/login - Login and get JWT token
- GET /api/v1/auth/me - Get current user info
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
)
from app.core.repositories import UserRepository
from app.core.dependencies import get_current_user
from app.models.database import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# Request/Response Models
# =============================================================================

class UserRegisterRequest(BaseModel):
    """Request body for user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")


class UserLoginRequest(BaseModel):
    """Request body for user login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    """User data in responses."""
    id: str
    email: str
    is_admin: bool
    is_active: bool


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


# =============================================================================
# Endpoints
# =============================================================================

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Email already registered"},
    }
)
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account.
    
    Returns a JWT token for immediate authentication.
    """
    repo = UserRepository(db)
    
    # Check if email already exists
    existing = await repo.get_by_email(request.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    hashed_password = get_password_hash(request.password)
    user = await repo.create(
        email=request.email,
        hashed_password=hashed_password,
        is_admin=False
    )
    
    # Generate token
    access_token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "is_admin": user.is_admin,
    })
    
    logger.info(f"New user registered: {user.email}")
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            is_admin=user.is_admin,
            is_active=user.is_active,
        )
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get access token",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"},
    }
)
async def login(
    request: UserLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return JWT token.
    """
    repo = UserRepository(db)
    
    # Find user
    user = await repo.get_by_email(request.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate token
    access_token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "is_admin": user.is_admin,
    })
    
    logger.info(f"User logged in: {user.email}")
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            is_admin=user.is_admin,
            is_active=user.is_active,
        )
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user info",
    responses={
        200: {"description": "Current user data"},
        401: {"description": "Not authenticated"},
    }
)
async def get_current_user_info(
    user: User = Depends(get_current_user),
):
    """
    Get the currently authenticated user's information.
    
    Requires valid JWT token in Authorization header.
    """
    return UserResponse(
        id=user.id,
        email=user.email,
        is_admin=user.is_admin,
        is_active=user.is_active,
    )
