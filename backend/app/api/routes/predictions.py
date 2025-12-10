"""
Predictions REST API routes for the Learning System.

Provides endpoints for:
- Listing user predictions with filters
- Getting prediction details
- Submitting user feedback on predictions
- Getting strategy performance statistics

All routes require authentication - predictions are scoped to users.
"""
import json
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    User, Prediction, StrategyType, PredictionStatus, PredictionOutcome,
)
from app.core.dependencies import get_current_user
from app.core.database import get_db
from app.core.repositories import PredictionRepository, GlobalInsightRepository

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class PredictionResponse(BaseModel):
    """Response model for a single prediction."""
    id: str
    strategy_type: str
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: List[float]
    timeframe: str
    confidence: str
    signals: List[str]
    analysis_summary: Optional[str]
    status: str
    outcome: Optional[str]
    actual_exit_price: Optional[float]
    accuracy_score: Optional[float]
    timing_score: Optional[float]
    rr_achieved: Optional[float]
    user_feedback: Optional[str]
    user_comment: Optional[str]
    created_at: datetime
    activated_at: Optional[datetime]
    closed_at: Optional[datetime]
    valid_until: Optional[datetime]

    class Config:
        from_attributes = True


class PredictionListResponse(BaseModel):
    """Response model for prediction list."""
    predictions: List[PredictionResponse]
    total: int
    has_more: bool


class FeedbackRequest(BaseModel):
    """Request to submit feedback on a prediction."""
    rating: str = Field(..., pattern="^(helpful|neutral|wrong)$")
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""
    success: bool
    message: str


class StrategyStatsResponse(BaseModel):
    """Response model for strategy performance statistics."""
    strategy_type: str
    period_days: int
    total: int
    active_count: int = 0
    win_rate: float
    avg_accuracy_score: float
    avg_rr_achieved: float
    outcomes: dict
    strengths: List[str] = []
    weaknesses: List[str] = []
    insights: List[str] = []


class GlobalInsightResponse(BaseModel):
    """Response model for a global insight."""
    id: str
    insight_type: str
    description: str
    source_strategy: Optional[str]
    applies_to_all: bool
    confidence: float
    evidence_count: int
    created_at: datetime


# =============================================================================
# Helper Functions
# =============================================================================

def prediction_to_response(prediction: Prediction) -> PredictionResponse:
    """Convert database Prediction model to response model."""
    try:
        take_profit = json.loads(prediction.take_profit_json) if prediction.take_profit_json else []
    except json.JSONDecodeError:
        take_profit = []
    
    try:
        signals = json.loads(prediction.signals_json) if prediction.signals_json else []
    except json.JSONDecodeError:
        signals = []
    
    return PredictionResponse(
        id=prediction.id,
        strategy_type=prediction.strategy_type.value if prediction.strategy_type else "unknown",
        symbol=prediction.symbol,
        direction=prediction.direction,
        entry_price=prediction.entry_price,
        stop_loss=prediction.stop_loss,
        take_profit=take_profit,
        timeframe=prediction.timeframe,
        confidence=prediction.confidence,
        signals=signals,
        analysis_summary=prediction.analysis_summary,
        status=prediction.status.value if prediction.status else "pending",
        outcome=prediction.outcome.value if prediction.outcome else None,
        actual_exit_price=prediction.actual_exit_price,
        accuracy_score=prediction.accuracy_score,
        timing_score=prediction.timing_score,
        rr_achieved=prediction.rr_achieved,
        user_feedback=prediction.user_feedback,
        user_comment=prediction.user_comment,
        created_at=prediction.created_at,
        activated_at=prediction.activated_at,
        closed_at=prediction.closed_at,
        valid_until=prediction.valid_until,
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/", response_model=PredictionListResponse)
async def list_predictions(
    strategy_type: Optional[str] = Query(None, description="Filter by strategy type"),
    status: Optional[str] = Query(None, description="Filter by status (pending, active, closed)"),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List predictions for the authenticated user.
    
    Supports filtering by strategy type and status.
    """
    repo = PredictionRepository(db)
    
    # Parse strategy type if provided
    strategy_filter = None
    if strategy_type:
        try:
            strategy_filter = StrategyType(strategy_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid strategy type: {strategy_type}"
            )
    
    # Parse status if provided
    status_filter = None
    if status:
        try:
            status_filter = PredictionStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}"
            )
    
    predictions = await repo.list_for_user(
        user_id=user.id,
        strategy_type=strategy_filter,
        status=status_filter,
        skip=skip,
        limit=limit + 1,  # Fetch one extra to check for more
    )
    
    has_more = len(predictions) > limit
    if has_more:
        predictions = predictions[:limit]
    
    return PredictionListResponse(
        predictions=[prediction_to_response(p) for p in predictions],
        total=len(predictions),
        has_more=has_more,
    )


@router.get("/stats", response_model=StrategyStatsResponse)
async def get_strategy_stats(
    strategy_type: str = Query(..., description="Strategy type to get stats for"),
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get performance statistics for a specific strategy.
    
    Returns win rate, average scores, and identified strengths/weaknesses.
    """
    try:
        strategy_enum = StrategyType(strategy_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy type: {strategy_type}"
        )
    
    from app.services.prediction_service import PredictionService
    
    service = PredictionService(db, user.id)
    
    # Get stats
    stats = await service.get_strategy_performance(strategy_enum, days)
    
    # Get strengths and weaknesses
    strengths = await service.identify_strengths(strategy_enum)
    weaknesses = await service.identify_weaknesses(strategy_enum)
    
    # Get insights
    insight_repo = GlobalInsightRepository(db)
    insights_db = await insight_repo.list_active(user.id, strategy_enum, limit=5)
    insights = [i.description for i in insights_db]
    
    return StrategyStatsResponse(
        strategy_type=strategy_type,
        period_days=days,
        total=stats["total"],
        active_count=stats.get("active_count", 0),
        win_rate=stats["win_rate"],
        avg_accuracy_score=stats["avg_accuracy_score"],
        avg_rr_achieved=stats["avg_rr_achieved"],
        outcomes=stats["outcomes"],
        strengths=strengths,
        weaknesses=weaknesses,
        insights=insights,
    )


@router.get("/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(
    prediction_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get details of a specific prediction.
    """
    repo = PredictionRepository(db)
    prediction = await repo.get_by_id(prediction_id, user.id)
    
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
    
    return prediction_to_response(prediction)


@router.post("/{prediction_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    prediction_id: str,
    request: FeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit user feedback on a prediction.
    
    Feedback helps improve the Learning System's scoring and insights.
    """
    repo = PredictionRepository(db)
    
    # Verify prediction exists and belongs to user
    prediction = await repo.get_by_id(prediction_id, user.id)
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
    
    # Add feedback
    success = await repo.add_user_feedback(
        prediction_id=prediction_id,
        user_id=user.id,
        feedback=request.rating,
        comment=request.comment,
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save feedback")
    
    logger.info(f"User {user.id} submitted feedback for prediction {prediction_id}: {request.rating}")
    
    return FeedbackResponse(
        success=True,
        message=f"Feedback '{request.rating}' saved successfully",
    )


@router.get("/insights/global", response_model=List[GlobalInsightResponse])
async def get_global_insights(
    strategy_type: Optional[str] = Query(None, description="Filter by strategy"),
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get global insights for the user.
    
    These are cross-strategy learnings identified from prediction patterns.
    """
    strategy_filter = None
    if strategy_type:
        try:
            strategy_filter = StrategyType(strategy_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid strategy type: {strategy_type}"
            )
    
    repo = GlobalInsightRepository(db)
    insights = await repo.list_active(
        user_id=user.id,
        strategy_type=strategy_filter,
        limit=limit,
    )
    
    return [
        GlobalInsightResponse(
            id=i.id,
            insight_type=i.insight_type.value if i.insight_type else "general",
            description=i.description,
            source_strategy=i.source_strategy.value if i.source_strategy else None,
            applies_to_all=i.applies_to_all,
            confidence=i.confidence,
            evidence_count=i.evidence_count,
            created_at=i.created_at,
        )
        for i in insights
    ]
