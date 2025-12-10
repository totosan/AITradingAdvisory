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


# =============================================================================
# Prediction Repository (Learning System)
# =============================================================================

from typing import Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_

from app.models.database import (
    Prediction, PredictionEvaluation, GlobalInsight,
    StrategyType, PredictionStatus, PredictionOutcome,
)


class PredictionRepository:
    """
    Repository for prediction operations.
    
    Supports strategy-isolated queries for the learning system.
    All operations are scoped to a specific user.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        user_id: str,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit_json: str,
        strategy_type: StrategyType = StrategyType.UNKNOWN,
        conversation_id: Optional[str] = None,
        timeframe: str = "4H",
        confidence: str = "medium",
        signals_json: Optional[str] = None,
        analysis_summary: Optional[str] = None,
        valid_until: Optional[datetime] = None,
    ) -> Prediction:
        """Create a new prediction."""
        prediction = Prediction(
            user_id=user_id,
            conversation_id=conversation_id,
            strategy_type=strategy_type,
            symbol=symbol.upper(),
            direction=direction.lower(),
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_json=take_profit_json,
            timeframe=timeframe,
            confidence=confidence,
            signals_json=signals_json,
            analysis_summary=analysis_summary,
            valid_until=valid_until,
            status=PredictionStatus.PENDING,
        )
        self.session.add(prediction)
        await self.session.flush()
        await self.session.refresh(prediction)
        return prediction
    
    async def get_by_id(self, prediction_id: str, user_id: str) -> Optional[Prediction]:
        """Get prediction by ID (must belong to user)."""
        result = await self.session.execute(
            select(Prediction)
            .where(Prediction.id == prediction_id)
            .where(Prediction.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def list_for_user(
        self,
        user_id: str,
        strategy_type: Optional[StrategyType] = None,
        status: Optional[PredictionStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Prediction]:
        """
        List predictions for a user with optional filters.
        
        Args:
            user_id: Owner user ID
            strategy_type: Filter by strategy (for isolated feedback)
            status: Filter by status (pending, active, closed, etc.)
            skip: Pagination offset
            limit: Maximum results
        """
        query = select(Prediction).where(Prediction.user_id == user_id)
        
        if strategy_type is not None:
            query = query.where(Prediction.strategy_type == strategy_type)
        
        if status is not None:
            query = query.where(Prediction.status == status)
        
        query = query.offset(skip).limit(limit).order_by(Prediction.created_at.desc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def list_active_for_evaluation(self) -> List[Prediction]:
        """
        Get all active predictions across all users for evaluation.
        
        Used by the background evaluation scheduler.
        """
        result = await self.session.execute(
            select(Prediction)
            .where(
                or_(
                    Prediction.status == PredictionStatus.PENDING,
                    Prediction.status == PredictionStatus.ACTIVE,
                )
            )
            .order_by(Prediction.created_at.asc())
        )
        return list(result.scalars().all())
    
    async def update_status(
        self,
        prediction_id: str,
        user_id: str,
        status: PredictionStatus,
        outcome: Optional[PredictionOutcome] = None,
        actual_exit_price: Optional[float] = None,
        accuracy_score: Optional[float] = None,
        timing_score: Optional[float] = None,
        rr_achieved: Optional[float] = None,
    ) -> bool:
        """Update prediction status and scores."""
        prediction = await self.get_by_id(prediction_id, user_id)
        if prediction is None:
            return False
        
        prediction.status = status
        if outcome is not None:
            prediction.outcome = outcome
        if actual_exit_price is not None:
            prediction.actual_exit_price = actual_exit_price
        if accuracy_score is not None:
            prediction.accuracy_score = accuracy_score
        if timing_score is not None:
            prediction.timing_score = timing_score
        if rr_achieved is not None:
            prediction.rr_achieved = rr_achieved
        
        if status == PredictionStatus.ACTIVE and prediction.activated_at is None:
            prediction.activated_at = datetime.utcnow()
        elif status == PredictionStatus.CLOSED:
            prediction.closed_at = datetime.utcnow()
        
        await self.session.flush()
        return True
    
    async def add_user_feedback(
        self,
        prediction_id: str,
        user_id: str,
        feedback: str,
        comment: Optional[str] = None,
    ) -> bool:
        """Add user feedback to a prediction."""
        prediction = await self.get_by_id(prediction_id, user_id)
        if prediction is None:
            return False
        
        prediction.user_feedback = feedback
        if comment:
            prediction.user_comment = comment
        
        await self.session.flush()
        return True
    
    async def get_strategy_stats(
        self,
        user_id: str,
        strategy_type: StrategyType,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get aggregated performance statistics for a strategy.
        
        Returns:
            Dict with win_rate, avg_score, total, outcomes breakdown, etc.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Get closed predictions for the strategy
        result = await self.session.execute(
            select(Prediction)
            .where(Prediction.user_id == user_id)
            .where(Prediction.strategy_type == strategy_type)
            .where(Prediction.status == PredictionStatus.CLOSED)
            .where(Prediction.created_at >= cutoff)
        )
        predictions = list(result.scalars().all())
        
        if not predictions:
            return {
                "strategy_type": strategy_type.value,
                "period_days": days,
                "total": 0,
                "win_rate": 0.0,
                "avg_accuracy_score": 0.0,
                "avg_rr_achieved": 0.0,
                "outcomes": {"win": 0, "loss": 0, "break_even": 0, "expired": 0},
            }
        
        # Calculate statistics
        outcomes = {"win": 0, "loss": 0, "break_even": 0, "expired": 0}
        scores = []
        rrs = []
        
        for p in predictions:
            if p.outcome:
                outcomes[p.outcome.value] = outcomes.get(p.outcome.value, 0) + 1
            if p.accuracy_score is not None:
                scores.append(p.accuracy_score)
            if p.rr_achieved is not None:
                rrs.append(p.rr_achieved)
        
        total = len(predictions)
        win_rate = (outcomes["win"] / total * 100) if total > 0 else 0.0
        avg_score = sum(scores) / len(scores) if scores else 0.0
        avg_rr = sum(rrs) / len(rrs) if rrs else 0.0
        
        return {
            "strategy_type": strategy_type.value,
            "period_days": days,
            "total": total,
            "win_rate": round(win_rate, 1),
            "avg_accuracy_score": round(avg_score, 1),
            "avg_rr_achieved": round(avg_rr, 2),
            "outcomes": outcomes,
        }
    
    async def get_recent_for_context(
        self,
        user_id: str,
        strategy_type: StrategyType,
        limit: int = 10,
    ) -> List[Prediction]:
        """
        Get recent predictions for feedback context injection.
        
        Returns most recent closed predictions for a strategy,
        used to build performance summary for agent prompts.
        """
        result = await self.session.execute(
            select(Prediction)
            .where(Prediction.user_id == user_id)
            .where(Prediction.strategy_type == strategy_type)
            .where(Prediction.status == PredictionStatus.CLOSED)
            .order_by(Prediction.closed_at.desc().nullslast())
            .limit(limit)
        )
        return list(result.scalars().all())


# =============================================================================
# Prediction Evaluation Repository
# =============================================================================

class PredictionEvaluationRepository:
    """Repository for prediction evaluation snapshots."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        prediction_id: str,
        current_price: float,
        distance_to_entry_pct: float,
        distance_to_sl_pct: float,
        distance_to_tp_pct: float,
        mfe: float = 0.0,
        mae: float = 0.0,
    ) -> PredictionEvaluation:
        """Create an evaluation snapshot."""
        evaluation = PredictionEvaluation(
            prediction_id=prediction_id,
            current_price=current_price,
            distance_to_entry_pct=distance_to_entry_pct,
            distance_to_sl_pct=distance_to_sl_pct,
            distance_to_tp_pct=distance_to_tp_pct,
            mfe=mfe,
            mae=mae,
        )
        self.session.add(evaluation)
        await self.session.flush()
        await self.session.refresh(evaluation)
        return evaluation
    
    async def list_for_prediction(
        self,
        prediction_id: str,
        limit: int = 50,
    ) -> List[PredictionEvaluation]:
        """Get evaluation history for a prediction."""
        result = await self.session.execute(
            select(PredictionEvaluation)
            .where(PredictionEvaluation.prediction_id == prediction_id)
            .order_by(PredictionEvaluation.evaluated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_latest(self, prediction_id: str) -> Optional[PredictionEvaluation]:
        """Get the most recent evaluation for a prediction."""
        result = await self.session.execute(
            select(PredictionEvaluation)
            .where(PredictionEvaluation.prediction_id == prediction_id)
            .order_by(PredictionEvaluation.evaluated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


# =============================================================================
# Global Insight Repository
# =============================================================================

class GlobalInsightRepository:
    """Repository for cross-strategy learning insights."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        user_id: str,
        insight_type: str,
        description: str,
        source_strategy: Optional[StrategyType] = None,
        applies_to_all: bool = False,
        confidence: float = 0.5,
        evidence_count: int = 1,
    ) -> GlobalInsight:
        """Create a new global insight."""
        from app.models.database import InsightType
        
        insight = GlobalInsight(
            user_id=user_id,
            insight_type=InsightType(insight_type) if isinstance(insight_type, str) else insight_type,
            description=description,
            source_strategy=source_strategy,
            applies_to_all=applies_to_all,
            confidence=confidence,
            evidence_count=evidence_count,
            is_active=True,
        )
        self.session.add(insight)
        await self.session.flush()
        await self.session.refresh(insight)
        return insight
    
    async def list_active(
        self,
        user_id: str,
        strategy_type: Optional[StrategyType] = None,
        limit: int = 10,
    ) -> List[GlobalInsight]:
        """
        Get active insights for a user.
        
        If strategy_type is specified, returns insights that:
        - Apply to all strategies, OR
        - Are specific to that strategy
        """
        query = (
            select(GlobalInsight)
            .where(GlobalInsight.user_id == user_id)
            .where(GlobalInsight.is_active == True)
        )
        
        if strategy_type is not None:
            query = query.where(
                or_(
                    GlobalInsight.applies_to_all == True,
                    GlobalInsight.source_strategy == strategy_type,
                )
            )
        
        query = query.order_by(GlobalInsight.confidence.desc()).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update_confidence(
        self,
        insight_id: str,
        user_id: str,
        new_confidence: float,
        evidence_count_delta: int = 0,
    ) -> bool:
        """Update insight confidence based on new evidence."""
        result = await self.session.execute(
            select(GlobalInsight)
            .where(GlobalInsight.id == insight_id)
            .where(GlobalInsight.user_id == user_id)
        )
        insight = result.scalar_one_or_none()
        if insight is None:
            return False
        
        insight.confidence = new_confidence
        insight.evidence_count += evidence_count_delta
        await self.session.flush()
        return True
    
    async def deactivate(self, insight_id: str, user_id: str) -> bool:
        """Deactivate an insight."""
        result = await self.session.execute(
            select(GlobalInsight)
            .where(GlobalInsight.id == insight_id)
            .where(GlobalInsight.user_id == user_id)
        )
        insight = result.scalar_one_or_none()
        if insight is None:
            return False
        
        insight.is_active = False
        await self.session.flush()
        return True
