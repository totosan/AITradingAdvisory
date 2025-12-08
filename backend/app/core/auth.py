"""
JWT Authentication module.

Handles:
- Password hashing with bcrypt
- JWT token creation and validation
- Admin user bootstrap at startup

Usage:
    from app.core.auth import verify_password, create_access_token, get_password_hash
    
    hashed = get_password_hash("mypassword")
    is_valid = verify_password("mypassword", hashed)
    token = create_access_token({"sub": user_id, "email": email})
"""
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.repositories import UserRepository

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Algorithm
ALGORITHM = "HS256"


class TokenData(BaseModel):
    """Data extracted from JWT token."""
    user_id: str
    email: str
    is_admin: bool = False


def get_jwt_secret() -> str:
    """
    Get JWT secret key.
    
    Uses JWT_SECRET_KEY from environment if set,
    otherwise generates a random secret (will change on restart).
    """
    settings = get_settings()
    if settings.jwt_secret_key:
        return settings.jwt_secret_key
    
    # Generate a random secret if not configured
    # WARNING: This will invalidate all tokens on restart
    logger.warning(
        "JWT_SECRET_KEY not set - generating random secret. "
        "Set JWT_SECRET_KEY in .env for persistent tokens."
    )
    return secrets.token_urlsafe(32)


# Cache the secret at module load
_jwt_secret: Optional[str] = None


def _get_secret() -> str:
    """Get cached JWT secret."""
    global _jwt_secret
    if _jwt_secret is None:
        _jwt_secret = get_jwt_secret()
    return _jwt_secret


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: The plain text password
        hashed_password: The bcrypt hashed password
    
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
    
    Returns:
        Bcrypt hashed password
    """
    return pwd_context.hash(password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary with token payload (must include "sub" for user ID)
        expires_delta: Optional expiration time delta
    
    Returns:
        Encoded JWT token string
    """
    settings = get_settings()
    
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, _get_secret(), algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Decode and validate a JWT access token.
    
    Args:
        token: The JWT token string
    
    Returns:
        TokenData if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, _get_secret(), algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email", "")
        is_admin: bool = payload.get("is_admin", False)
        
        if user_id is None:
            return None
        
        return TokenData(user_id=user_id, email=email, is_admin=is_admin)
    except JWTError as e:
        logger.debug(f"JWT decode error: {e}")
        return None


async def bootstrap_admin_user(admin_email: str) -> None:
    """
    Create admin user at startup if not exists.
    
    The admin user is created with a random password that is logged.
    In production, change this password immediately.
    
    Args:
        admin_email: Email for the admin user
    """
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        repo = UserRepository(session)
        
        # Check if admin already exists
        existing = await repo.get_by_email(admin_email)
        if existing:
            logger.info(f"Admin user already exists: {admin_email}")
            return
        
        # Generate random password
        temp_password = secrets.token_urlsafe(16)
        hashed_password = get_password_hash(temp_password)
        
        # Create admin user
        user = await repo.create(
            email=admin_email,
            hashed_password=hashed_password,
            is_admin=True
        )
        await session.commit()
        
        # Log the temporary password (only at startup)
        logger.info(f"Created admin user: {admin_email}")
        print(f"   Admin user created: {admin_email}")
        print(f"   Temporary password: {temp_password}")
        print(f"   ⚠️  Change this password immediately!")


async def authenticate_user(email: str, password: str) -> Optional[Any]:
    """
    Authenticate a user by email and password.
    
    Args:
        email: User email
        password: Plain text password
    
    Returns:
        User object if authenticated, None otherwise
    """
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_email(email)
        
        if user is None:
            return None
        
        if not user.is_active:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        return user
