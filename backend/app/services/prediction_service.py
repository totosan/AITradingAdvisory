"""
Prediction Service for the Learning System.

Handles the full prediction lifecycle:
1. Extract predictions from agent responses (JSON parsing)
2. Save predictions with user/conversation/strategy context
3. Evaluate predictions against actual market outcomes
4. Calculate accuracy scores

Usage:
    from app.services.prediction_service import PredictionService
    
    service = PredictionService(session, user_id)
    predictions = service.extract_predictions_from_message(agent_response)
    for pred_data in predictions:
        await service.save_prediction(pred_data, conversation_id)
"""
import json
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    Prediction, PredictionStatus, PredictionOutcome, StrategyType,
)
from app.core.repositories import (
    PredictionRepository, PredictionEvaluationRepository, GlobalInsightRepository,
)

logger = logging.getLogger(__name__)


# Patterns to find prediction JSON in agent responses
PREDICTION_PATTERNS = [
    # Explicit JSON block with entry_setups
    r'"entry_setups"\s*:\s*(\[[\s\S]*?\])',
    # Standalone entry object
    r'\{[^{}]*"type"\s*:\s*"(?:long|short)"[^{}]*"entry"\s*:\s*[\d.]+[^{}]*\}',
    r'\{[^{}]*"entry_price"\s*:\s*[\d.]+[^{}]*"stop_loss"\s*:\s*[\d.]+[^{}]*\}',
    r'\{[^{}]*"direction"\s*:\s*"(?:long|short)"[^{}]*\}',
]


class PredictionService:
    """
    Service for managing trading predictions in the learning system.
    
    Provides methods to:
    - Extract predictions from agent output
    - Save predictions with strategy classification
    - Evaluate predictions against market data
    - Calculate accuracy scores
    """
    
    def __init__(self, session: AsyncSession, user_id: str):
        """
        Initialize the prediction service.
        
        Args:
            session: Database session
            user_id: Current user ID (for scoped operations)
        """
        self.session = session
        self.user_id = user_id
        self.prediction_repo = PredictionRepository(session)
        self.evaluation_repo = PredictionEvaluationRepository(session)
        self.insight_repo = GlobalInsightRepository(session)
    
    def extract_predictions_from_message(
        self,
        content: str,
        symbol: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract prediction data from agent response content.
        
        Searches for JSON structures containing entry/SL/TP information.
        
        Args:
            content: Agent response text (may contain JSON)
            symbol: Optional symbol override (if not in JSON)
            
        Returns:
            List of prediction dictionaries ready for save_prediction()
            
        Example extracted prediction:
            {
                "symbol": "BTCUSDT",
                "direction": "long",
                "entry_price": 98500,
                "stop_loss": 97000,
                "take_profit": [100000, 102000],
                "confidence": "high",
                "signals": ["RSI oversold", "MACD bullish cross"],
                "timeframe": "4H"
            }
        """
        predictions = []
        
        # Try to find entry_setups array first (from generate_strategy_visualization)
        entry_setups_match = re.search(r'"entry_setups"\s*:\s*(\[[\s\S]*?\])', content)
        if entry_setups_match:
            try:
                setups = json.loads(entry_setups_match.group(1))
                for setup in setups:
                    pred = self._normalize_prediction(setup, symbol)
                    if pred:
                        predictions.append(pred)
                if predictions:
                    logger.info(f"Extracted {len(predictions)} predictions from entry_setups")
                    return predictions
            except json.JSONDecodeError:
                pass
        
        # Try to find individual prediction objects
        json_pattern = r'\{[^{}]*(?:"type"|"direction"|"entry_price"|"entry")[^{}]*\}'
        for match in re.finditer(json_pattern, content):
            try:
                obj = json.loads(match.group())
                pred = self._normalize_prediction(obj, symbol)
                if pred:
                    predictions.append(pred)
            except json.JSONDecodeError:
                continue
        
        if predictions:
            logger.info(f"Extracted {len(predictions)} predictions from content")
        
        return predictions
    
    def _normalize_prediction(
        self,
        data: Dict[str, Any],
        default_symbol: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Normalize prediction data to a standard format.
        
        Handles various input formats from different agents.
        """
        # Extract direction
        direction = data.get("direction") or data.get("type")
        if direction not in ("long", "short"):
            # Try to infer from text
            direction = "long" if direction in ("buy", "bullish") else "short" if direction in ("sell", "bearish") else None
        
        if not direction:
            return None
        
        # Extract entry price
        entry_price = (
            data.get("entry_price") or 
            data.get("entry") or 
            data.get("trigger_price") or
            data.get("price")
        )
        if not entry_price:
            return None
        
        # Extract stop loss
        stop_loss = data.get("stop_loss") or data.get("sl") or data.get("stop")
        if not stop_loss:
            return None
        
        # Extract take profit (can be single value or array)
        take_profit = data.get("take_profit") or data.get("tp") or data.get("target")
        if take_profit is None:
            take_profit = []
        elif not isinstance(take_profit, list):
            take_profit = [take_profit]
        
        # Extract symbol
        symbol = data.get("symbol") or default_symbol
        if not symbol:
            return None
        
        # Normalize symbol format
        symbol = symbol.upper()
        if not symbol.endswith("USDT") and len(symbol) <= 5:
            symbol = f"{symbol}USDT"
        
        return {
            "symbol": symbol,
            "direction": direction.lower(),
            "entry_price": float(entry_price),
            "stop_loss": float(stop_loss),
            "take_profit": [float(tp) for tp in take_profit],
            "confidence": data.get("confidence", "medium"),
            "signals": data.get("signals", []),
            "timeframe": data.get("timeframe", "4H"),
            "trigger_condition": data.get("trigger_condition"),
            "invalidation": data.get("invalidation"),
        }
    
    async def save_prediction(
        self,
        prediction_data: Dict[str, Any],
        strategy_type: StrategyType = StrategyType.UNKNOWN,
        conversation_id: Optional[str] = None,
        analysis_summary: Optional[str] = None,
        valid_hours: int = 48,
    ) -> Prediction:
        """
        Save a prediction to the database.
        
        Args:
            prediction_data: Normalized prediction dict from extract_predictions_from_message
            strategy_type: Trading strategy classification
            conversation_id: Optional link to conversation
            analysis_summary: Optional summary text
            valid_hours: How long the prediction is valid (default 48h)
            
        Returns:
            Created Prediction model instance
        """
        take_profit_json = json.dumps(prediction_data.get("take_profit", []))
        signals_json = json.dumps(prediction_data.get("signals", []))
        
        valid_until = datetime.utcnow() + timedelta(hours=valid_hours)
        
        prediction = await self.prediction_repo.create(
            user_id=self.user_id,
            symbol=prediction_data["symbol"],
            direction=prediction_data["direction"],
            entry_price=prediction_data["entry_price"],
            stop_loss=prediction_data["stop_loss"],
            take_profit_json=take_profit_json,
            strategy_type=strategy_type,
            conversation_id=conversation_id,
            timeframe=prediction_data.get("timeframe", "4H"),
            confidence=prediction_data.get("confidence", "medium"),
            signals_json=signals_json,
            analysis_summary=analysis_summary,
            valid_until=valid_until,
        )
        
        logger.info(
            f"Saved prediction {prediction.id}: {prediction.symbol} "
            f"{prediction.direction} @ {prediction.entry_price}"
        )
        
        return prediction
    
    async def evaluate_prediction(
        self,
        prediction: Prediction,
        current_price: float,
    ) -> Tuple[bool, Optional[PredictionOutcome]]:
        """
        Evaluate a prediction against current market price.
        
        Updates prediction status and creates evaluation snapshot.
        
        Args:
            prediction: Prediction to evaluate
            current_price: Current market price
            
        Returns:
            Tuple of (status_changed, new_outcome)
        """
        # Parse take profit levels
        try:
            take_profits = json.loads(prediction.take_profit_json)
        except json.JSONDecodeError:
            take_profits = []
        
        first_tp = take_profits[0] if take_profits else prediction.entry_price * 1.05
        
        # Calculate distances
        distance_to_entry = ((current_price - prediction.entry_price) / prediction.entry_price) * 100
        distance_to_sl = ((current_price - prediction.stop_loss) / prediction.stop_loss) * 100
        distance_to_tp = ((current_price - first_tp) / first_tp) * 100
        
        # Get previous evaluation for MFE/MAE calculation
        prev_eval = await self.evaluation_repo.get_latest(prediction.id)
        
        # Calculate MFE and MAE
        if prediction.direction == "long":
            profit_pct = ((current_price - prediction.entry_price) / prediction.entry_price) * 100
        else:
            profit_pct = ((prediction.entry_price - current_price) / prediction.entry_price) * 100
        
        mfe = max(prev_eval.mfe if prev_eval else 0, profit_pct if profit_pct > 0 else 0)
        mae = max(prev_eval.mae if prev_eval else 0, abs(profit_pct) if profit_pct < 0 else 0)
        
        # Create evaluation snapshot
        await self.evaluation_repo.create(
            prediction_id=prediction.id,
            current_price=current_price,
            distance_to_entry_pct=distance_to_entry,
            distance_to_sl_pct=distance_to_sl,
            distance_to_tp_pct=distance_to_tp,
            mfe=mfe,
            mae=mae,
        )
        
        # Check for status changes
        status_changed = False
        new_outcome = None
        
        # Check if expired
        if prediction.valid_until and datetime.utcnow() > prediction.valid_until:
            if prediction.status in (PredictionStatus.PENDING, PredictionStatus.ACTIVE):
                status_changed = True
                new_outcome = PredictionOutcome.EXPIRED
                await self._close_prediction(prediction, new_outcome, current_price, mfe, mae)
                return (status_changed, new_outcome)
        
        # Check if entry triggered (pending -> active)
        if prediction.status == PredictionStatus.PENDING:
            entry_triggered = False
            if prediction.direction == "long":
                entry_triggered = current_price <= prediction.entry_price
            else:
                entry_triggered = current_price >= prediction.entry_price
            
            if entry_triggered:
                prediction.status = PredictionStatus.ACTIVE
                prediction.activated_at = datetime.utcnow()
                await self.session.flush()
                status_changed = True
                logger.info(f"Prediction {prediction.id} activated at {current_price}")
        
        # Check for SL/TP hit (active -> closed)
        if prediction.status == PredictionStatus.ACTIVE:
            if prediction.direction == "long":
                # Long: SL hit if price <= SL, TP hit if price >= TP
                if current_price <= prediction.stop_loss:
                    new_outcome = PredictionOutcome.LOSS
                elif take_profits and current_price >= take_profits[0]:
                    new_outcome = PredictionOutcome.WIN
            else:
                # Short: SL hit if price >= SL, TP hit if price <= TP
                if current_price >= prediction.stop_loss:
                    new_outcome = PredictionOutcome.LOSS
                elif take_profits and current_price <= take_profits[0]:
                    new_outcome = PredictionOutcome.WIN
            
            if new_outcome:
                status_changed = True
                await self._close_prediction(prediction, new_outcome, current_price, mfe, mae)
        
        return (status_changed, new_outcome)
    
    async def _close_prediction(
        self,
        prediction: Prediction,
        outcome: PredictionOutcome,
        exit_price: float,
        mfe: float,
        mae: float,
    ) -> None:
        """Close a prediction and calculate scores."""
        # Calculate scores
        accuracy_score = self._calculate_accuracy_score(prediction, outcome, mfe, mae)
        timing_score = self._calculate_timing_score(prediction)
        rr_achieved = self._calculate_rr_achieved(prediction, exit_price)
        
        # Update prediction
        await self.prediction_repo.update_status(
            prediction_id=prediction.id,
            user_id=prediction.user_id,
            status=PredictionStatus.CLOSED,
            outcome=outcome,
            actual_exit_price=exit_price,
            accuracy_score=accuracy_score,
            timing_score=timing_score,
            rr_achieved=rr_achieved,
        )
        
        logger.info(
            f"Prediction {prediction.id} closed: {outcome.value} "
            f"(score: {accuracy_score:.1f}, R:R: {rr_achieved:.2f})"
        )
    
    def _calculate_accuracy_score(
        self,
        prediction: Prediction,
        outcome: PredictionOutcome,
        mfe: float,
        mae: float,
    ) -> float:
        """
        Calculate accuracy score (0-100) for a prediction.
        
        Scoring:
        - Direction correct (win): +40 points
        - Direction partially correct (break_even): +20 points
        - Good MFE (reached profit before reversal): +20 points
        - Low MAE (minimal drawdown): +20 points
        - Quick resolution: +20 points
        """
        score = 0.0
        
        # Direction score
        if outcome == PredictionOutcome.WIN:
            score += 40
        elif outcome == PredictionOutcome.BREAK_EVEN:
            score += 20
        
        # MFE score (how far into profit did we go?)
        if mfe > 0:
            mfe_score = min(mfe / 3.0, 1.0) * 20  # Cap at 3% MFE for full score
            score += mfe_score
        
        # MAE score (inverse - less drawdown is better)
        if mae < 5:
            mae_score = (1 - mae / 5.0) * 20  # Full score if MAE < 5%
            score += mae_score
        
        # Resolution speed (bonus for quick wins, handled in timing_score)
        # Placeholder - timing handled separately
        
        return min(100, max(0, score))
    
    def _calculate_timing_score(self, prediction: Prediction) -> float:
        """
        Calculate timing score based on how quickly prediction resolved.
        
        Fast wins score higher, slow losses score lower.
        """
        if not prediction.activated_at or not prediction.closed_at:
            return 50.0  # Default middle score
        
        duration = (prediction.closed_at - prediction.activated_at).total_seconds() / 3600  # hours
        
        # Quick resolution (< 24h) is good for wins, bad for losses
        if prediction.outcome == PredictionOutcome.WIN:
            if duration < 24:
                return 80 + (24 - duration) / 24 * 20  # Up to 100
            else:
                return max(50, 80 - (duration - 24) / 48 * 30)  # Down to 50
        else:
            # For losses, slow stop-out suggests good entry timing
            if duration > 24:
                return 60.0
            else:
                return 40.0
        
        return 50.0
    
    def _calculate_rr_achieved(
        self,
        prediction: Prediction,
        exit_price: float,
    ) -> float:
        """Calculate actual risk/reward ratio achieved."""
        risk = abs(prediction.entry_price - prediction.stop_loss)
        if risk == 0:
            return 0.0
        
        if prediction.direction == "long":
            reward = exit_price - prediction.entry_price
        else:
            reward = prediction.entry_price - exit_price
        
        return reward / risk
    
    async def get_strategy_performance(
        self,
        strategy_type: StrategyType,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get performance statistics for a strategy.
        
        Wrapper around repository method with additional analysis.
        """
        stats = await self.prediction_repo.get_strategy_stats(
            user_id=self.user_id,
            strategy_type=strategy_type,
            days=days,
        )
        
        # Add active predictions count
        active_predictions = await self.prediction_repo.list_for_user(
            user_id=self.user_id,
            strategy_type=strategy_type,
            status=PredictionStatus.ACTIVE,
        )
        stats["active_count"] = len(active_predictions)
        
        return stats
    
    async def identify_weaknesses(
        self,
        strategy_type: StrategyType,
    ) -> List[str]:
        """
        Identify weaknesses in recent predictions for a strategy.
        
        Analyzes patterns in closed predictions to find improvement areas.
        
        Returns:
            List of weakness descriptions
        """
        weaknesses = []
        
        predictions = await self.prediction_repo.get_recent_for_context(
            user_id=self.user_id,
            strategy_type=strategy_type,
            limit=20,
        )
        
        if len(predictions) < 5:
            return ["Nicht genug Daten für Analyse (mind. 5 Predictions)"]
        
        # Analyze SL hits
        sl_hits_early = 0
        for p in predictions:
            if p.outcome == PredictionOutcome.LOSS:
                evals = await self.evaluation_repo.list_for_prediction(p.id, limit=10)
                if evals and evals[0].mfe > 1.0:  # Was in profit before SL hit
                    sl_hits_early += 1
        
        if sl_hits_early / len(predictions) > 0.2:
            weaknesses.append(f"SL wird zu früh getriggert ({sl_hits_early}x war Trade im Plus vor SL)")
        
        # Analyze confidence calibration
        high_conf_losses = sum(1 for p in predictions 
                             if p.confidence == "high" and p.outcome == PredictionOutcome.LOSS)
        low_conf_wins = sum(1 for p in predictions 
                          if p.confidence == "low" and p.outcome == PredictionOutcome.WIN)
        
        if high_conf_losses > len(predictions) * 0.3:
            weaknesses.append("High-Confidence Predictions haben hohe Loss-Rate")
        
        if low_conf_wins > len(predictions) * 0.3:
            weaknesses.append("Low-Confidence Predictions performen besser als erwartet")
        
        return weaknesses
    
    async def identify_strengths(
        self,
        strategy_type: StrategyType,
    ) -> List[str]:
        """
        Identify strengths in recent predictions for a strategy.
        
        Returns:
            List of strength descriptions
        """
        strengths = []
        
        predictions = await self.prediction_repo.get_recent_for_context(
            user_id=self.user_id,
            strategy_type=strategy_type,
            limit=20,
        )
        
        if len(predictions) < 5:
            return []
        
        # Calculate win rate
        wins = sum(1 for p in predictions if p.outcome == PredictionOutcome.WIN)
        win_rate = wins / len(predictions) * 100
        
        if win_rate > 60:
            strengths.append(f"Starke Win-Rate ({win_rate:.0f}%)")
        
        # Check average R:R
        rrs = [p.rr_achieved for p in predictions if p.rr_achieved is not None]
        if rrs:
            avg_rr = sum(rrs) / len(rrs)
            if avg_rr > 1.5:
                strengths.append(f"Gutes R:R-Verhältnis (Ø {avg_rr:.1f})")
        
        # Check timing
        good_timing = sum(1 for p in predictions 
                        if p.timing_score and p.timing_score > 70)
        if good_timing / len(predictions) > 0.5:
            strengths.append("Gutes Entry-Timing bei Mehrheit der Trades")
        
        return strengths
