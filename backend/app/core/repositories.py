"""
Repository pattern for data access.

Provides abstraction layer for database operations.
Designed for easy migration from SQLite to Azure SQL.

Usage:
    from app.core.repositories import UserRepository
    
    repo = UserRepository(session)
    user = await repo.get_by_email("user@example.com")
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import User, Conversation, Message


# =============================================================================
# User Repository
# =============================================================================

class UserRepositoryProtocol(Protocol):
    """
    Protocol for user repository operations.
    
    Implement this protocol for different backends:
    - SQLiteUserRepository (local development)
    - AzureSQLUserRepository (production)
    """
    
    async def create(self, email: str, hashed_password: str, is_admin: bool = False) -> User:
        """Create a new user."""
        ...
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        ...
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        ...
    
    async def update_password(self, user_id: str, hashed_password: str) -> bool:
        """Update user's password."""
        ...
    
    async def deactivate(self, user_id: str) -> bool:
        """Deactivate a user account."""
        ...
    
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List all users with pagination."""
        ...


class UserRepository:
    """
    SQLite/SQL implementation of user repository.
    
    Works with both SQLite (dev) and Azure SQL (prod).
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self, 
        email: str, 
        hashed_password: str, 
        is_admin: bool = False
    ) -> User:
        """Create a new user."""
        user = User(
            email=email.lower().strip(),
            hashed_password=hashed_password,
            is_admin=is_admin,
            is_active=True,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email (case-insensitive)."""
        result = await self.session.execute(
            select(User).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()
    
    async def update_password(self, user_id: str, hashed_password: str) -> bool:
        """Update user's password."""
        user = await self.get_by_id(user_id)
        if user is None:
            return False
        user.hashed_password = hashed_password
        await self.session.flush()
        return True
    
    async def deactivate(self, user_id: str) -> bool:
        """Deactivate a user account."""
        user = await self.get_by_id(user_id)
        if user is None:
            return False
        user.is_active = False
        await self.session.flush()
        return True
    
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List all active users with pagination."""
        result = await self.session.execute(
            select(User)
            .where(User.is_active == True)
            .offset(skip)
            .limit(limit)
            .order_by(User.created_at.desc())
        )
        return list(result.scalars().all())


# =============================================================================
# Conversation Repository
# =============================================================================

class ConversationRepository:
    """
    Repository for conversation operations.
    
    All operations are scoped to a specific user for security.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, user_id: str, title: str = "New Conversation") -> Conversation:
        """Create a new conversation for a user."""
        conversation = Conversation(
            user_id=user_id,
            title=title,
        )
        self.session.add(conversation)
        await self.session.flush()
        await self.session.refresh(conversation)
        return conversation
    
    async def get_by_id(self, conversation_id: str, user_id: str) -> Optional[Conversation]:
        """Get conversation by ID (must belong to user)."""
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .where(Conversation.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def list_for_user(
        self, 
        user_id: str, 
        skip: int = 0, 
        limit: int = 50
    ) -> List[Conversation]:
        """List all conversations for a user."""
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(Conversation.updated_at.desc().nullslast())
        )
        return list(result.scalars().all())
    
    async def update_title(
        self, 
        conversation_id: str, 
        user_id: str, 
        title: str
    ) -> bool:
        """Update conversation title."""
        conversation = await self.get_by_id(conversation_id, user_id)
        if conversation is None:
            return False
        conversation.title = title
        await self.session.flush()
        return True
    
    async def delete(self, conversation_id: str, user_id: str) -> bool:
        """Delete a conversation and all its messages."""
        conversation = await self.get_by_id(conversation_id, user_id)
        if conversation is None:
            return False
        await self.session.delete(conversation)
        await self.session.flush()
        return True


# =============================================================================
# Message Repository
# =============================================================================

class MessageRepository:
    """
    Repository for message operations.
    
    Messages are accessed through their parent conversation.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self, 
        conversation_id: str, 
        role: str, 
        content: str,
        metadata_json: Optional[str] = None
    ) -> Message:
        """Create a new message in a conversation."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata_json=metadata_json,
        )
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message
    
    async def list_for_conversation(
        self, 
        conversation_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """Get all messages in a conversation (ordered by time)."""
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .offset(skip)
            .limit(limit)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())
    
    async def count_for_conversation(self, conversation_id: str) -> int:
        """Count messages in a conversation."""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(Message.id))
            .where(Message.conversation_id == conversation_id)
        )
        return result.scalar_one()
