"""
Market Phase Detector for AITradingAdvisory

Automatically detects the current market phase to enable
intelligent agent team routing.

Market Phases:
- RANGING: Price consolidating between support and resistance
- TRENDING_UP: Clear bullish trend
- TRENDING_DOWN: Clear bearish trend
- BREAKOUT_PENDING: Compressed volatility, breakout imminent
- VOLATILE: High volatility, unpredictable movements
- REVERSAL_POSSIBLE: Signs of trend exhaustion

Detection Logic:
- ADX < 25 → RANGING
- ADX > 25 + EMA alignment → TRENDING
- Narrow Bollinger + Price near zone → BREAKOUT_PENDING
- RSI divergence + Price at zone → REVERSAL_POSSIBLE
"""

import json
import logging
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np

# Add src to path for keylevel_analyzer
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

logger = logging.getLogger(__name__)


class MarketPhase(Enum):
    """Market phase classifications."""
    RANGING = "ranging"
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    BREAKOUT_PENDING = "breakout_pending"
    VOLATILE = "volatile"
    REVERSAL_POSSIBLE = "reversal_possible"


@dataclass
class PhaseIndicators:
    """Technical indicators used for phase detection."""
    adx: float
    plus_di: float
    minus_di: float
    rsi: float
    rsi_ma: float
    bb_width: float
    bb_position: float  # 0=lower band, 0.5=middle, 1=upper band
    ema_20: float
    ema_50: float
    ema_200: float
    atr: float
    atr_percent: float  # ATR as percentage of price
    price_in_zone: bool
    zone_type: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "adx": round(self.adx, 2),
            "plus_di": round(self.plus_di, 2),
            "minus_di": round(self.minus_di, 2),
            "rsi": round(self.rsi, 2),
            "rsi_ma": round(self.rsi_ma, 2),
            "bb_width": round(self.bb_width, 4),
            "bb_position": round(self.bb_position, 2),
            "ema_20": round(self.ema_20, 2),
            "ema_50": round(self.ema_50, 2),
            "ema_200": round(self.ema_200, 2),
            "atr": round(self.atr, 2),
            "atr_percent": round(self.atr_percent, 4),
            "price_in_zone": self.price_in_zone,
            "zone_type": self.zone_type,
        }


@dataclass
class MarketPhaseResult:
    """Result of market phase detection."""
    phase: MarketPhase
    confidence: float  # 0.0 to 1.0
    indicators: PhaseIndicators
    range_info: Optional[Dict[str, float]]
    recommendation: str
    supporting_factors: List[str]
    conflicting_factors: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase.value,
            "confidence": round(self.confidence, 2),
            "indicators": self.indicators.to_dict(),
            "range": self.range_info,
            "recommendation": self.recommendation,
            "supporting_factors": self.supporting_factors,
            "conflicting_factors": self.conflicting_factors,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class MarketPhaseDetector:
    """
    Detects the current market phase from OHLCV data.
    
    Uses multiple indicators to determine market conditions:
    - ADX for trend strength
    - RSI for momentum
    - Bollinger Bands for volatility compression
    - EMA alignment for trend direction
    - Key levels for range detection
    
    Args:
        adx_period: Period for ADX calculation (default: 14)
        adx_trending_threshold: ADX value above which market is trending (default: 25)
        adx_strong_threshold: ADX value for strong trend (default: 40)
        rsi_period: Period for RSI calculation (default: 14)
        rsi_ma_period: Period for RSI moving average (default: 14)
        bb_period: Period for Bollinger Bands (default: 20)
        bb_std: Standard deviation for Bollinger Bands (default: 2.0)
        bb_squeeze_threshold: BB width below which is considered a squeeze (default: 0.04)
        volatility_threshold: ATR% above which is considered volatile (default: 0.05)
    """
    
    def __init__(
        self,
        adx_period: int = 14,
        adx_trending_threshold: float = 25.0,
        adx_strong_threshold: float = 40.0,
        rsi_period: int = 14,
        rsi_ma_period: int = 14,
        bb_period: int = 20,
        bb_std: float = 2.0,
        bb_squeeze_threshold: float = 0.04,
        volatility_threshold: float = 0.05,
    ):
        self.adx_period = adx_period
        self.adx_trending_threshold = adx_trending_threshold
        self.adx_strong_threshold = adx_strong_threshold
        self.rsi_period = rsi_period
        self.rsi_ma_period = rsi_ma_period
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.bb_squeeze_threshold = bb_squeeze_threshold
        self.volatility_threshold = volatility_threshold
    
    def _calculate_ema(self, series: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return series.ewm(span=period, adjust=False).mean()
    
    def _calculate_rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> tuple:
        """
        Calculate ADX, +DI, and -DI.
        
        Returns:
            Tuple of (ADX, +DI, -DI) series
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Calculate True Range
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate Directional Movement
        prev_high = high.shift(1)
        prev_low = low.shift(1)
        
        plus_dm = high - prev_high
        minus_dm = prev_low - low
        
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        
        # Smooth with EMA
        atr = true_range.ewm(span=period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)
        
        # Calculate DX and ADX
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
        adx = dx.ewm(span=period, adjust=False).mean()
        
        return adx, plus_di, minus_di
    
    def _calculate_bollinger_bands(
        self,
        close: pd.Series,
        period: int = 20,
        std_dev: float = 2.0,
    ) -> tuple:
        """
        Calculate Bollinger Bands.
        
        Returns:
            Tuple of (upper, middle, lower, width, position)
        """
        middle = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        # Width as percentage of middle band
        width = (upper - lower) / middle
        
        # Position: 0 = at lower band, 0.5 = at middle, 1 = at upper band
        position = (close - lower) / (upper - lower)
        
        return upper, middle, lower, width, position
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.ewm(span=period, adjust=False).mean()
        
        return atr
    
    def _get_key_level_info(self, df: pd.DataFrame) -> tuple:
        """
        Get key level information using KeyLevelAnalyzer.
        
        Returns:
            Tuple of (price_in_zone, zone_type, range_info)
        """
        try:
            from keylevel_analyzer import KeyLevelAnalyzer
            
            analyzer = KeyLevelAnalyzer()
            result = analyzer.analyze(df)
            
            price_in_zone = result.current_position.in_zone
            zone_type = result.current_position.zone_type
            range_info = result.range_info
            
            return price_in_zone, zone_type, range_info
        except Exception as e:
            logger.warning(f"Could not analyze key levels: {e}")
            return False, None, None
    
    def _detect_rsi_divergence(
        self,
        close: pd.Series,
        rsi: pd.Series,
        lookback: int = 10,
    ) -> tuple:
        """
        Detect RSI divergence.
        
        Returns:
            Tuple of (has_bullish_divergence, has_bearish_divergence)
        """
        if len(close) < lookback + 1:
            return False, False
        
        recent_close = close.iloc[-lookback:]
        recent_rsi = rsi.iloc[-lookback:]
        
        # Bullish divergence: price making lower lows but RSI making higher lows
        close_trend = recent_close.iloc[-1] - recent_close.iloc[0]
        rsi_trend = recent_rsi.iloc[-1] - recent_rsi.iloc[0]
        
        bullish_div = close_trend < 0 and rsi_trend > 0
        bearish_div = close_trend > 0 and rsi_trend < 0
        
        return bullish_div, bearish_div
    
    def _calculate_indicators(self, df: pd.DataFrame) -> PhaseIndicators:
        """Calculate all indicators needed for phase detection."""
        close = df['close']
        current_price = close.iloc[-1]
        
        # ADX
        adx, plus_di, minus_di = self._calculate_adx(df, self.adx_period)
        
        # RSI
        rsi = self._calculate_rsi(close, self.rsi_period)
        rsi_ma = rsi.rolling(window=self.rsi_ma_period).mean()
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower, bb_width, bb_position = self._calculate_bollinger_bands(
            close, self.bb_period, self.bb_std
        )
        
        # EMAs
        ema_20 = self._calculate_ema(close, 20)
        ema_50 = self._calculate_ema(close, 50)
        ema_200 = self._calculate_ema(close, 200)
        
        # ATR
        atr = self._calculate_atr(df, 14)
        atr_percent = atr.iloc[-1] / current_price
        
        # Key levels
        price_in_zone, zone_type, _ = self._get_key_level_info(df)
        
        return PhaseIndicators(
            adx=adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0,
            plus_di=plus_di.iloc[-1] if not pd.isna(plus_di.iloc[-1]) else 0,
            minus_di=minus_di.iloc[-1] if not pd.isna(minus_di.iloc[-1]) else 0,
            rsi=rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50,
            rsi_ma=rsi_ma.iloc[-1] if not pd.isna(rsi_ma.iloc[-1]) else 50,
            bb_width=bb_width.iloc[-1] if not pd.isna(bb_width.iloc[-1]) else 0.05,
            bb_position=bb_position.iloc[-1] if not pd.isna(bb_position.iloc[-1]) else 0.5,
            ema_20=ema_20.iloc[-1] if not pd.isna(ema_20.iloc[-1]) else current_price,
            ema_50=ema_50.iloc[-1] if not pd.isna(ema_50.iloc[-1]) else current_price,
            ema_200=ema_200.iloc[-1] if not pd.isna(ema_200.iloc[-1]) else current_price,
            atr=atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0,
            atr_percent=atr_percent,
            price_in_zone=price_in_zone,
            zone_type=zone_type,
        )
    
    def detect(self, df: pd.DataFrame) -> MarketPhaseResult:
        """
        Detect the current market phase.
        
        Args:
            df: DataFrame with OHLCV columns
            
        Returns:
            MarketPhaseResult with phase, confidence, and supporting data
        """
        # Validate input
        required_cols = ['open', 'high', 'low', 'close']
        df = df.copy()
        df.columns = df.columns.str.lower()
        
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"DataFrame missing required columns: {missing}")
        
        if len(df) < 50:
            logger.warning("DataFrame may be too short for reliable phase detection")
        
        # Calculate all indicators
        indicators = self._calculate_indicators(df)
        
        # Get key level info
        _, _, range_info = self._get_key_level_info(df)
        
        # RSI divergence
        close = df['close']
        rsi = self._calculate_rsi(close, self.rsi_period)
        bullish_div, bearish_div = self._detect_rsi_divergence(close, rsi)
        
        # Scoring system for each phase
        phase_scores = {
            MarketPhase.RANGING: 0.0,
            MarketPhase.TRENDING_UP: 0.0,
            MarketPhase.TRENDING_DOWN: 0.0,
            MarketPhase.BREAKOUT_PENDING: 0.0,
            MarketPhase.VOLATILE: 0.0,
            MarketPhase.REVERSAL_POSSIBLE: 0.0,
        }
        
        supporting_factors = []
        conflicting_factors = []
        
        current_price = close.iloc[-1]
        
        # ========== RANGING Detection ==========
        # Low ADX indicates no trend
        if indicators.adx < self.adx_trending_threshold:
            phase_scores[MarketPhase.RANGING] += 0.4
            supporting_factors.append(f"ADX {indicators.adx:.1f} < {self.adx_trending_threshold} (no trend)")
        
        # Price between EMAs
        ema_range = max(indicators.ema_20, indicators.ema_50) - min(indicators.ema_20, indicators.ema_50)
        if current_price > min(indicators.ema_20, indicators.ema_50) and \
           current_price < max(indicators.ema_20, indicators.ema_50):
            phase_scores[MarketPhase.RANGING] += 0.2
            supporting_factors.append("Price between EMA20 and EMA50")
        
        # RSI near 50
        if 40 < indicators.rsi < 60:
            phase_scores[MarketPhase.RANGING] += 0.2
            supporting_factors.append(f"RSI {indicators.rsi:.1f} near neutral (40-60)")
        
        # Price in a key level zone
        if indicators.price_in_zone:
            phase_scores[MarketPhase.RANGING] += 0.1
            supporting_factors.append(f"Price at {indicators.zone_type} zone")
        
        # ========== TRENDING UP Detection ==========
        if indicators.adx >= self.adx_trending_threshold and indicators.plus_di > indicators.minus_di:
            phase_scores[MarketPhase.TRENDING_UP] += 0.4
            supporting_factors.append(f"ADX {indicators.adx:.1f} with +DI > -DI (uptrend)")
        
        # EMA alignment (20 > 50 > 200)
        if indicators.ema_20 > indicators.ema_50 > indicators.ema_200:
            phase_scores[MarketPhase.TRENDING_UP] += 0.3
            supporting_factors.append("EMA alignment: 20 > 50 > 200")
        
        # Price above all EMAs
        if current_price > indicators.ema_20 > indicators.ema_50:
            phase_scores[MarketPhase.TRENDING_UP] += 0.2
            supporting_factors.append("Price above EMA20 and EMA50")
        
        # RSI above 50
        if indicators.rsi > 55:
            phase_scores[MarketPhase.TRENDING_UP] += 0.1
            supporting_factors.append(f"RSI {indicators.rsi:.1f} bullish (>55)")
        
        # ========== TRENDING DOWN Detection ==========
        if indicators.adx >= self.adx_trending_threshold and indicators.minus_di > indicators.plus_di:
            phase_scores[MarketPhase.TRENDING_DOWN] += 0.4
            supporting_factors.append(f"ADX {indicators.adx:.1f} with -DI > +DI (downtrend)")
        
        # EMA alignment (20 < 50 < 200)
        if indicators.ema_20 < indicators.ema_50 < indicators.ema_200:
            phase_scores[MarketPhase.TRENDING_DOWN] += 0.3
            supporting_factors.append("EMA alignment: 20 < 50 < 200")
        
        # Price below all EMAs
        if current_price < indicators.ema_20 < indicators.ema_50:
            phase_scores[MarketPhase.TRENDING_DOWN] += 0.2
            supporting_factors.append("Price below EMA20 and EMA50")
        
        # RSI below 50
        if indicators.rsi < 45:
            phase_scores[MarketPhase.TRENDING_DOWN] += 0.1
            supporting_factors.append(f"RSI {indicators.rsi:.1f} bearish (<45)")
        
        # ========== BREAKOUT PENDING Detection ==========
        # Bollinger Band squeeze
        if indicators.bb_width < self.bb_squeeze_threshold:
            phase_scores[MarketPhase.BREAKOUT_PENDING] += 0.5
            supporting_factors.append(f"BB squeeze: width {indicators.bb_width:.4f} < {self.bb_squeeze_threshold}")
        
        # Price near key level
        if indicators.price_in_zone:
            phase_scores[MarketPhase.BREAKOUT_PENDING] += 0.2
            supporting_factors.append(f"Price at {indicators.zone_type} - potential breakout zone")
        
        # Low ADX but building
        if 15 < indicators.adx < 25:
            phase_scores[MarketPhase.BREAKOUT_PENDING] += 0.2
            supporting_factors.append(f"ADX {indicators.adx:.1f} building strength")
        
        # ========== VOLATILE Detection ==========
        # High ATR relative to price
        if indicators.atr_percent > self.volatility_threshold:
            phase_scores[MarketPhase.VOLATILE] += 0.5
            supporting_factors.append(f"High volatility: ATR {indicators.atr_percent*100:.2f}% of price")
        
        # Wide Bollinger Bands
        if indicators.bb_width > 0.1:
            phase_scores[MarketPhase.VOLATILE] += 0.3
            supporting_factors.append(f"Wide BB: {indicators.bb_width:.4f}")
        
        # ========== REVERSAL POSSIBLE Detection ==========
        # RSI divergence
        if bullish_div and indicators.rsi < 40:
            phase_scores[MarketPhase.REVERSAL_POSSIBLE] += 0.4
            supporting_factors.append("Bullish RSI divergence at oversold")
        
        if bearish_div and indicators.rsi > 60:
            phase_scores[MarketPhase.REVERSAL_POSSIBLE] += 0.4
            supporting_factors.append("Bearish RSI divergence at overbought")
        
        # Price at key level with extreme RSI
        if indicators.price_in_zone:
            if indicators.zone_type == "support" and indicators.rsi < 35:
                phase_scores[MarketPhase.REVERSAL_POSSIBLE] += 0.3
                supporting_factors.append("Oversold at support - potential bounce")
            elif indicators.zone_type == "resistance" and indicators.rsi > 65:
                phase_scores[MarketPhase.REVERSAL_POSSIBLE] += 0.3
                supporting_factors.append("Overbought at resistance - potential reversal")
        
        # Extreme RSI
        if indicators.rsi < 25 or indicators.rsi > 75:
            phase_scores[MarketPhase.REVERSAL_POSSIBLE] += 0.2
            extreme = "oversold" if indicators.rsi < 25 else "overbought"
            supporting_factors.append(f"Extreme RSI {indicators.rsi:.1f} ({extreme})")
        
        # Find the highest scoring phase
        best_phase = max(phase_scores, key=phase_scores.get)
        confidence = min(phase_scores[best_phase], 1.0)
        
        # Generate recommendation
        recommendations = {
            MarketPhase.RANGING: f"Range-Trading empfohlen: Buy at support ({range_info['low'] if range_info else 'N/A'}), sell at resistance ({range_info['high'] if range_info else 'N/A'})",
            MarketPhase.TRENDING_UP: "Trend-Following empfohlen: Look for pullbacks to EMA20/50 for long entries",
            MarketPhase.TRENDING_DOWN: "Trend-Following (short) empfohlen: Look for rallies to EMA20/50 for short entries",
            MarketPhase.BREAKOUT_PENDING: "Breakout-Setup empfohlen: Prepare for breakout, set alerts at key levels",
            MarketPhase.VOLATILE: "Vorsicht: Hohe Volatilität - Reduzierte Positionsgrößen empfohlen",
            MarketPhase.REVERSAL_POSSIBLE: "Reversal-Watch: Auf Bestätigungs-Patterns achten (Engulfing, Hammer, etc.)",
        }
        
        return MarketPhaseResult(
            phase=best_phase,
            confidence=confidence,
            indicators=indicators,
            range_info=range_info,
            recommendation=recommendations[best_phase],
            supporting_factors=list(set(supporting_factors)),  # Remove duplicates
            conflicting_factors=conflicting_factors,
        )


# ============================================================================
# Tool Function for Agent Integration
# ============================================================================

def detect_market_phase(
    symbol: str,
    interval: str = "1H",
    bars: int = 200,
) -> str:
    """
    Detect the current market phase for a trading pair.
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT', 'ETHUSDT')
        interval: Timeframe interval (e.g., '1H', '4H', '1D')
        bars: Number of bars to analyze
    
    Returns:
        JSON string with phase, confidence, indicators, and recommendation
    """
    try:
        from exchange_tools import get_ohlcv_data
        
        # Fetch OHLCV data
        ohlcv_json = get_ohlcv_data(symbol=symbol, interval=interval, limit=bars)
        ohlcv_data = json.loads(ohlcv_json)
        
        if "error" in ohlcv_data:
            return json.dumps({"error": ohlcv_data["error"]})
        
        candles = ohlcv_data.get("candles", [])
        if not candles:
            return json.dumps({"error": "No candle data returned"})
        
        df = pd.DataFrame(candles)
        
        # Detect phase
        detector = MarketPhaseDetector()
        result = detector.detect(df)
        
        # Add metadata
        output = result.to_dict()
        output["symbol"] = symbol
        output["interval"] = interval
        output["bars_analyzed"] = len(df)
        output["current_price"] = float(df['close'].iloc[-1])
        
        return json.dumps(output, indent=2)
    
    except Exception as e:
        logger.error(f"Error detecting market phase: {e}")
        return json.dumps({"error": str(e)})
