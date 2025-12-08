"""
SQLAlchemy database models for multi-user support.

Models:
- User: User accounts with email/password auth
- Conversation: Chat conversations per user
- Message: Individual messages in conversations

Designed for SQLite locally, migrable to Azure SQL.
"""
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class User(Base):
    """
    User account model.
    
    Attributes:
        id: Unique identifier (UUID)
        email: User email (unique, used for login)
        hashed_password: bcrypt hashed password
        is_admin: Whether user has admin privileges
        is_active: Whether account is active
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=generate_uuid
    )
    email: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        index=True, 
        nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), 
        nullable=False
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean, 
        default=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, 
        default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, 
        onupdate=datetime.utcnow,
        nullable=True
    )
    
    # Relationships
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, is_admin={self.is_admin})>"


class Conversation(Base):
    """
    Chat conversation model.
    
    Each user can have multiple conversations.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Owner user ID
        title: Conversation title (auto-generated or user-set)
        created_at: Creation timestamp
        updated_at: Last message timestamp
    """
    __tablename__ = "conversations"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=generate_uuid
    )
    user_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(
        String(255), 
        default="New Conversation"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, 
        onupdate=datetime.utcnow,
        nullable=True
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="conversations"
    )
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )
    
    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, title={self.title})>"


class Message(Base):
    """
    Chat message model.
    
    Stores individual messages within a conversation.
    
    Attributes:
        id: Auto-increment primary key
        conversation_id: Parent conversation ID
        role: Message role (user, assistant, system)
        content: Message content (text/markdown)
        metadata: Optional JSON metadata (tool calls, charts, etc.)
        created_at: Message timestamp
    """
    __tablename__ = "messages"
    
    id: Mapped[int] = mapped_column(
        Integer, 
        primary_key=True, 
        autoincrement=True
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role: Mapped[str] = mapped_column(
        String(50), 
        nullable=False
    )  # "user", "assistant", "system"
    content: Mapped[str] = mapped_column(
        Text, 
        nullable=False
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )  # JSON string for extra data
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow
    )
    
    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages"
    )
    
    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role={self.role})>"
