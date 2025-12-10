"""
SQLAlchemy database models for multi-user support.

Models:
- User: User accounts with email/password auth
- Conversation: Chat conversations per user
- Message: Individual messages in conversations
- Prediction: Trading predictions with strategy type
- PredictionEvaluation: Market snapshots for prediction evaluation
- GlobalInsight: Cross-strategy learnings

Designed for SQLite locally, migrable to Azure SQL.
"""
import enum
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# =============================================================================
# Enums
# =============================================================================

class StrategyType(str, enum.Enum):
    """Trading strategy types for prediction categorization."""
    RANGE = "range"                      # Range/channel trading
    BREAKOUT_PULLBACK = "breakout_pullback"  # Breakout with pullback entry
    TREND_FOLLOWING = "trend_following"  # Trend/momentum trading
    REVERSAL = "reversal"                # Counter-trend reversals
    SCALPING = "scalping"                # Short-term scalping
    UNKNOWN = "unknown"                  # Uncategorized/unknown


class PredictionStatus(str, enum.Enum):
    """Status of a trading prediction."""
    PENDING = "pending"      # Not yet active (price hasn't reached entry)
    ACTIVE = "active"        # Trade is live
    CLOSED = "closed"        # Trade completed (win/loss/break_even)
    EXPIRED = "expired"      # Prediction validity expired
    CANCELLED = "cancelled"  # User cancelled


class PredictionOutcome(str, enum.Enum):
    """Outcome of a closed prediction."""
    WIN = "win"
    LOSS = "loss"
    BREAK_EVEN = "break_even"
    EXPIRED = "expired"


class InsightType(str, enum.Enum):
    """Types of global insights."""
    SL_TOO_TIGHT = "sl_too_tight"
    SL_TOO_WIDE = "sl_too_wide"
    ENTRY_TIMING = "entry_timing"
    TIMEFRAME_PREFERENCE = "timeframe_preference"
    SYMBOL_PERFORMANCE = "symbol_performance"
    CONFIDENCE_CALIBRATION = "confidence_calibration"
    GENERAL = "general"


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


# =============================================================================
# Learning System Models
# =============================================================================

class Prediction(Base):
    """
    Trading prediction model.
    
    Stores predictions made by agents with strategy type for isolated feedback.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Owner user ID
        conversation_id: Optional link to conversation where prediction was made
        strategy_type: Type of trading strategy (for isolated feedback)
        symbol: Trading pair (e.g., 'BTCUSDT')
        direction: 'long' or 'short'
        entry_price: Entry price level
        stop_loss: Stop loss price
        take_profit_json: JSON array of take profit levels
        timeframe: Analysis timeframe (e.g., '4H')
        confidence: Prediction confidence (high/medium/low)
        signals_json: JSON array of signal descriptions
        analysis_summary: Brief analysis text
        status: Current status (pending/active/closed/expired)
        outcome: Final outcome (win/loss/break_even/expired)
        actual_exit_price: Price at which position was closed
        accuracy_score: Calculated accuracy (0-100)
        timing_score: How well timed was the entry (0-100)
        rr_achieved: Actual risk/reward ratio achieved
        user_feedback: User rating (helpful/neutral/wrong)
        user_comment: Optional user comment
        created_at: Prediction creation timestamp
        activated_at: When entry was triggered
        closed_at: When position was closed
        valid_until: Prediction expiry time
    """
    __tablename__ = "predictions"
    
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
    conversation_id: Mapped[Optional[str]] = mapped_column(
        String(36), 
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Strategy & Trade Details
    strategy_type: Mapped[StrategyType] = mapped_column(
        Enum(StrategyType),
        default=StrategyType.UNKNOWN,
        index=True
    )
    symbol: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    direction: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )  # "long" or "short"
    entry_price: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    stop_loss: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    take_profit_json: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )  # JSON array: [100000, 102000, 105000]
    timeframe: Mapped[str] = mapped_column(
        String(10),
        default="4H"
    )
    
    # Analysis Context
    confidence: Mapped[str] = mapped_column(
        String(20),
        default="medium"
    )  # "high", "medium", "low"
    signals_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )  # JSON array of signal strings
    analysis_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Status & Outcome
    status: Mapped[PredictionStatus] = mapped_column(
        Enum(PredictionStatus),
        default=PredictionStatus.PENDING
    )
    outcome: Mapped[Optional[PredictionOutcome]] = mapped_column(
        Enum(PredictionOutcome),
        nullable=True
    )
    actual_exit_price: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    
    # Scores (calculated after close)
    accuracy_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )  # 0-100
    timing_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )  # 0-100
    rr_achieved: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )  # Actual R:R ratio
    
    # User Feedback
    user_feedback: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True
    )  # "helpful", "neutral", "wrong"
    user_comment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow
    )
    activated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    valid_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User")
    conversation: Mapped[Optional["Conversation"]] = relationship("Conversation")
    evaluations: Mapped[List["PredictionEvaluation"]] = relationship(
        "PredictionEvaluation",
        back_populates="prediction",
        cascade="all, delete-orphan",
        order_by="PredictionEvaluation.evaluated_at"
    )
    
    def __repr__(self) -> str:
        return f"<Prediction(id={self.id}, symbol={self.symbol}, strategy={self.strategy_type.value})>"


class PredictionEvaluation(Base):
    """
    Prediction evaluation snapshot.
    
    Tracks market state at various points during prediction lifetime.
    Used to calculate MFE (Max Favorable Excursion) and MAE (Max Adverse Excursion).
    
    Attributes:
        id: Auto-increment primary key
        prediction_id: Parent prediction ID
        evaluated_at: Timestamp of evaluation
        current_price: Market price at evaluation
        distance_to_entry_pct: % distance to entry price
        distance_to_sl_pct: % distance to stop loss
        distance_to_tp_pct: % distance to first take profit
        mfe: Maximum favorable excursion (best profit seen)
        mae: Maximum adverse excursion (worst loss seen)
    """
    __tablename__ = "prediction_evaluations"
    
    id: Mapped[int] = mapped_column(
        Integer, 
        primary_key=True, 
        autoincrement=True
    )
    prediction_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("predictions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow
    )
    current_price: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    distance_to_entry_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    distance_to_sl_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    distance_to_tp_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    mfe: Mapped[float] = mapped_column(
        Float,
        default=0.0
    )  # Max favorable excursion
    mae: Mapped[float] = mapped_column(
        Float,
        default=0.0
    )  # Max adverse excursion
    
    # Relationships
    prediction: Mapped["Prediction"] = relationship(
        "Prediction",
        back_populates="evaluations"
    )
    
    def __repr__(self) -> str:
        return f"<PredictionEvaluation(id={self.id}, price={self.current_price})>"


class GlobalInsight(Base):
    """
    Cross-strategy learning insights.
    
    Stores patterns and learnings that apply across strategies or globally.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Owner user ID
        insight_type: Type of insight (sl_too_tight, timeframe_preference, etc.)
        description: Human-readable insight description
        source_strategy: Strategy that generated this insight (if strategy-specific)
        applies_to_all: Whether insight applies to all strategies
        confidence: Confidence score (0.0-1.0)
        evidence_count: Number of predictions supporting this insight
        is_active: Whether insight is currently active
        created_at: When insight was generated
        updated_at: Last update timestamp
    """
    __tablename__ = "global_insights"
    
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
    
    insight_type: Mapped[InsightType] = mapped_column(
        Enum(InsightType),
        default=InsightType.GENERAL
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    source_strategy: Mapped[Optional[StrategyType]] = mapped_column(
        Enum(StrategyType),
        nullable=True
    )
    applies_to_all: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        default=0.5
    )  # 0.0-1.0
    evidence_count: Mapped[int] = mapped_column(
        Integer,
        default=1
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
    user: Mapped["User"] = relationship("User")
    
    def __repr__(self) -> str:
        return f"<GlobalInsight(id={self.id}, type={self.insight_type.value})>"
