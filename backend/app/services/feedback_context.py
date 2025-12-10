"""
Feedback Context Service for the Learning System.

Generates token-efficient feedback context for agent prompts.
Designed to stay within ~200 tokens while providing actionable insights.

Usage:
    from app.services.feedback_context import FeedbackContextService
    
    service = FeedbackContextService(session, user_id)
    context = await service.get_strategy_context(StrategyType.BREAKOUT_PULLBACK)
    
    # Inject into agent prompt
    enhanced_prompt = f"{base_prompt}\n\n{context}"
"""
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import StrategyType, PredictionOutcome
from app.core.repositories import (
    PredictionRepository, GlobalInsightRepository,
)
from app.services.prediction_service import PredictionService

logger = logging.getLogger(__name__)


# Strategy type display names (German/English)
STRATEGY_NAMES = {
    StrategyType.RANGE: "Range-Trading",
    StrategyType.BREAKOUT_PULLBACK: "Breakout-Pullback",
    StrategyType.TREND_FOLLOWING: "Trend-Following",
    StrategyType.REVERSAL: "Reversal",
    StrategyType.SCALPING: "Scalping",
    StrategyType.UNKNOWN: "Unbekannt",
}


class FeedbackContextService:
    """
    Service for generating token-efficient feedback context.
    
    Creates compact summaries (~100-200 tokens) of:
    - Strategy-specific performance metrics
    - Identified strengths and weaknesses
    - Global insights that apply
    - Actionable tips for improvement
    """
    
    def __init__(self, session: AsyncSession, user_id: str):
        """
        Initialize the feedback context service.
        
        Args:
            session: Database session
            user_id: Current user ID
        """
        self.session = session
        self.user_id = user_id
        self.prediction_repo = PredictionRepository(session)
        self.insight_repo = GlobalInsightRepository(session)
        self.prediction_service = PredictionService(session, user_id)
    
    async def get_strategy_context(
        self,
        strategy_type: StrategyType,
        max_tokens: int = 200,
    ) -> str:
        """
        Generate feedback context for a specific strategy.
        
        The output is designed to be injected into agent system prompts
        to make agents aware of their past performance.
        
        Args:
            strategy_type: The trading strategy to get context for
            max_tokens: Approximate token budget (default 200)
            
        Returns:
            Formatted string ready for prompt injection
            
        Example output:
            [DEIN PERFORMANCE FEEDBACK - Breakout-Pullback]
            Letzte 10: 70% Win, Score Ø75
            Stärken: Gutes Entry-Timing, R:R > 1.5
            Schwächen: SL 3x zu früh getriggert
            Tipp: Erweitere SL um 0.3% bei Volatilität
        """
        if strategy_type == StrategyType.UNKNOWN:
            return ""
        
        strategy_name = STRATEGY_NAMES.get(strategy_type, strategy_type.value)
        
        # Get performance stats
        stats = await self.prediction_service.get_strategy_performance(
            strategy_type=strategy_type,
            days=30,
        )
        
        # If no data, return minimal context
        if stats["total"] == 0:
            return f"""[PERFORMANCE FEEDBACK - {strategy_name}]
Noch keine {strategy_name} Predictions. Dies ist deine erste Analyse mit dieser Strategie."""
        
        # Get strengths and weaknesses
        strengths = await self.prediction_service.identify_strengths(strategy_type)
        weaknesses = await self.prediction_service.identify_weaknesses(strategy_type)
        
        # Get relevant global insights
        insights = await self.insight_repo.list_active(
            user_id=self.user_id,
            strategy_type=strategy_type,
            limit=3,
        )
        
        # Build compact context
        lines = [f"[DEIN PERFORMANCE FEEDBACK - {strategy_name}]"]
        
        # Performance line
        win_rate = stats["win_rate"]
        avg_score = stats["avg_accuracy_score"]
        total = stats["total"]
        lines.append(f"Letzte {total}: {win_rate:.0f}% Win, Score Ø{avg_score:.0f}")
        
        # Strengths (max 2)
        if strengths:
            strengths_str = ", ".join(strengths[:2])
            lines.append(f"Stärken: {strengths_str}")
        
        # Weaknesses (max 2)
        if weaknesses:
            weaknesses_str = ", ".join(weaknesses[:2])
            lines.append(f"Schwächen: {weaknesses_str}")
        
        # Top insight as tip
        if insights:
            top_insight = insights[0]
            lines.append(f"Tipp: {top_insight.description}")
        elif weaknesses:
            # Generate tip from weakness
            tip = self._generate_tip_from_weakness(weaknesses[0])
            if tip:
                lines.append(f"Tipp: {tip}")
        
        context = "\n".join(lines)
        
        # Token estimation (rough: ~0.75 tokens per word)
        word_count = len(context.split())
        estimated_tokens = int(word_count * 0.75)
        
        logger.debug(f"Generated feedback context: ~{estimated_tokens} tokens")
        
        return context
    
    def _generate_tip_from_weakness(self, weakness: str) -> Optional[str]:
        """Generate an actionable tip from a weakness description."""
        weakness_lower = weakness.lower()
        
        if "sl" in weakness_lower and ("früh" in weakness_lower or "eng" in weakness_lower):
            return "Erweitere SL um 0.3-0.5% für mehr Spielraum"
        
        if "confidence" in weakness_lower and "high" in weakness_lower:
            return "Reduziere Position-Size bei High-Confidence Trades"
        
        if "confidence" in weakness_lower and "low" in weakness_lower:
            return "Überprüfe Confidence-Kriterien - Low-Conf Trades könnten unterbewertet sein"
        
        return None
    
    async def get_global_context(self, max_tokens: int = 100) -> str:
        """
        Get strategy-agnostic global insights.
        
        For use when strategy type is unknown or for general analysis.
        
        Args:
            max_tokens: Approximate token budget
            
        Returns:
            Formatted string with global insights
        """
        insights = await self.insight_repo.list_active(
            user_id=self.user_id,
            strategy_type=None,  # Get all
            limit=3,
        )
        
        if not insights:
            return ""
        
        lines = ["[GLOBALE INSIGHTS]"]
        for insight in insights:
            lines.append(f"• {insight.description}")
        
        return "\n".join(lines)
    
    async def get_combined_context(
        self,
        strategy_type: Optional[StrategyType] = None,
        include_global: bool = True,
    ) -> str:
        """
        Get combined strategy + global context.
        
        Useful for comprehensive feedback injection.
        
        Args:
            strategy_type: Specific strategy (None for global only)
            include_global: Whether to include global insights
            
        Returns:
            Combined context string
        """
        parts = []
        
        # Strategy-specific context
        if strategy_type and strategy_type != StrategyType.UNKNOWN:
            strategy_context = await self.get_strategy_context(strategy_type)
            if strategy_context:
                parts.append(strategy_context)
        
        # Global context
        if include_global:
            global_context = await self.get_global_context()
            if global_context:
                parts.append(global_context)
        
        if not parts:
            return ""
        
        return "\n\n".join(parts)
    
    async def should_inject_feedback(
        self,
        strategy_type: StrategyType,
        min_predictions: int = 3,
    ) -> bool:
        """
        Check if feedback should be injected for this strategy.
        
        Returns False if there's not enough data to provide useful feedback.
        
        Args:
            strategy_type: The strategy to check
            min_predictions: Minimum closed predictions required
            
        Returns:
            True if feedback injection is worthwhile
        """
        if strategy_type == StrategyType.UNKNOWN:
            return False
        
        predictions = await self.prediction_repo.get_recent_for_context(
            user_id=self.user_id,
            strategy_type=strategy_type,
            limit=min_predictions,
        )
        
        return len(predictions) >= min_predictions


# =============================================================================
# Prompt Templates for Feedback Injection
# =============================================================================

FEEDBACK_INJECTION_TEMPLATE = """
═══════════════════════════════════════════════════════════════════════════════
📊 DEIN PERFORMANCE FEEDBACK (berücksichtige bei der Analyse)
═══════════════════════════════════════════════════════════════════════════════

{feedback_context}

Nutze diese Erkenntnisse um deine Analyse zu verbessern:
- Bei bekannten Schwächen: Kompensiere aktiv
- Bei Stärken: Nutze bewährte Ansätze
- Beachte globale Tipps für bessere Ergebnisse

═══════════════════════════════════════════════════════════════════════════════
"""


def format_feedback_for_prompt(feedback_context: str) -> str:
    """
    Format feedback context for injection into agent prompts.
    
    Wraps the context with visual separators for clarity.
    
    Args:
        feedback_context: Raw feedback from FeedbackContextService
        
    Returns:
        Formatted string ready for prompt concatenation
    """
    if not feedback_context or not feedback_context.strip():
        return ""
    
    return FEEDBACK_INJECTION_TEMPLATE.format(feedback_context=feedback_context)
