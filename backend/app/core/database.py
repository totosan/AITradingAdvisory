"""
Database configuration and session management.

Uses SQLAlchemy async with SQLite for local development.
Designed for easy migration to Azure SQL Database later.

Usage:
    from app.core.database import get_db, init_db
    
    # Initialize database (call once at startup)
    await init_db()
    
    # Use in routes with dependency injection
    async def my_route(db: AsyncSession = Depends(get_db)):
        ...
"""
import logging
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# Global engine and session factory (initialized lazily)
_engine = None
_async_session_factory = None


def get_database_url() -> str:
    """
    Get the database URL.
    
    For local development: SQLite in /app/data/app.db
    For Azure: Connection string from environment variable
    """
    settings = get_settings()
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # SQLite async URL format
    db_path = data_dir / "app.db"
    return f"sqlite+aiosqlite:///{db_path}"


def get_engine():
    """Get or create the async database engine."""
    global _engine
    if _engine is None:
        database_url = get_database_url()
        _engine = create_async_engine(
            database_url,
            echo=False,  # Set to True for SQL debugging
            # SQLite-specific settings
            connect_args={"check_same_thread": False},
        )
        logger.info(f"Database engine created: {database_url}")
    return _engine


def get_session_factory():
    """Get or create the async session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_engine()
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.
    
    Usage in FastAPI routes:
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """
    Initialize the database by creating all tables.
    
    Call this once at application startup.
    """
    # Import models to ensure they're registered with Base
    from app.models.database import User, Conversation, Message  # noqa: F401
    
    engine = get_engine()
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created successfully")


async def close_db() -> None:
    """
    Close the database connection.
    
    Call this at application shutdown.
    """
    global _engine, _async_session_factory
    
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
        logger.info("Database connection closed")
