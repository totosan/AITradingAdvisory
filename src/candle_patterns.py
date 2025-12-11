"""
Candle Pattern Scanner for AITradingAdvisory

Detects candlestick patterns with ATR-based size filtering.
Optionally filters patterns to only show those occurring at Key Levels.

Ported from Bjorgum Key Levels PineScript indicator pattern detection.

Pattern Types:
- Bullish: Hammer, Bullish Engulfing, Dragonfly Doji, Tweezer Bottom,
           Piercing, Bullish Harami, Long Lower Shadow
- Bearish: Shooting Star, Bearish Engulfing, Gravestone Doji, Tweezer Top,
           Dark Cloud Cover, Bearish Harami, Long Upper Shadow
- Neutral: Doji, Spinning Top

Usage:
    scanner = CandlePatternScanner()
    patterns = scanner.scan(df, zones=key_level_zones, only_at_levels=True)
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Annotated, Optional, List, Dict, Any
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Candlestick pattern types."""
    # Bullish patterns
    HAMMER = "hammer"
    BULLISH_ENGULFING = "bullish_engulfing"
    DRAGONFLY_DOJI = "dragonfly_doji"
    TWEEZER_BOTTOM = "tweezer_bottom"
    PIERCING = "piercing"
    BULLISH_HARAMI = "bullish_harami"
    LONG_LOWER_SHADOW = "long_lower_shadow"
    
    # Bearish patterns
    SHOOTING_STAR = "shooting_star"
    BEARISH_ENGULFING = "bearish_engulfing"
    GRAVESTONE_DOJI = "gravestone_doji"
    TWEEZER_TOP = "tweezer_top"
    DARK_CLOUD_COVER = "dark_cloud_cover"
    BEARISH_HARAMI = "bearish_harami"
    LONG_UPPER_SHADOW = "long_upper_shadow"
    
    # Neutral patterns
    DOJI = "doji"
    SPINNING_TOP = "spinning_top"


class PatternDirection(Enum):
    """Pattern directional bias."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


# Pattern to direction mapping
PATTERN_DIRECTION: Dict[PatternType, PatternDirection] = {
    PatternType.HAMMER: PatternDirection.BULLISH,
    PatternType.BULLISH_ENGULFING: PatternDirection.BULLISH,
    PatternType.DRAGONFLY_DOJI: PatternDirection.BULLISH,
    PatternType.TWEEZER_BOTTOM: PatternDirection.BULLISH,
    PatternType.PIERCING: PatternDirection.BULLISH,
    PatternType.BULLISH_HARAMI: PatternDirection.BULLISH,
    PatternType.LONG_LOWER_SHADOW: PatternDirection.BULLISH,
    PatternType.SHOOTING_STAR: PatternDirection.BEARISH,
    PatternType.BEARISH_ENGULFING: PatternDirection.BEARISH,
    PatternType.GRAVESTONE_DOJI: PatternDirection.BEARISH,
    PatternType.TWEEZER_TOP: PatternDirection.BEARISH,
    PatternType.DARK_CLOUD_COVER: PatternDirection.BEARISH,
    PatternType.BEARISH_HARAMI: PatternDirection.BEARISH,
    PatternType.LONG_UPPER_SHADOW: PatternDirection.BEARISH,
    PatternType.DOJI: PatternDirection.NEUTRAL,
    PatternType.SPINNING_TOP: PatternDirection.NEUTRAL,
}


@dataclass
class PatternMatch:
    """Represents a detected candlestick pattern."""
    pattern_type: PatternType
    direction: PatternDirection
    bar_index: int
    price: float
    confidence: float  # 0.0 to 1.0
    at_key_level: bool
    zone_type: Optional[str] = None  # "support" or "resistance"
    pattern_bars: int = 1  # Number of bars in the pattern
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern_type.value,
            "direction": self.direction.value,
            "bar_index": self.bar_index,
            "price": round(self.price, 2),
            "confidence": round(self.confidence, 2),
            "at_key_level": self.at_key_level,
            "zone_type": self.zone_type,
            "pattern_bars": self.pattern_bars,
        }


class CandlePatternScanner:
    """
    Detects candlestick patterns with ATR-based size filtering.
    
    Ported from Bjorgum Key Levels PineScript with the following features:
    - 16 pattern types (bullish, bearish, neutral)
    - ATR-based size filters to avoid micro-patterns
    - Optional filtering to only detect patterns at key levels
    - Configurable pattern detection parameters
    
    Args:
        atr_length: ATR calculation period (default: 14)
        hammer_fib: Body/candle ratio for hammers (default: 33%)
        doji_size: Max body/candle ratio for doji (default: 5%)
        shadow_percent: Max opposing shadow for hammers (default: 5%)
        min_size_atr: Minimum candle size as ATR multiple (default: 0.1)
        max_size_atr: Maximum candle size as ATR multiple, 0 = disabled (default: 0)
        long_shadow_ratio: Min shadow/candle ratio for long shadows (default: 75%)
        doji_wick_ratio: Max wick imbalance for doji (default: 2.0)
        engulf_wick: Engulfing must engulf wick (default: False)
        color_match: Hammer/star must match candle color (default: False)
        tweezer_half: Tweezer must close beyond half (default: False)
    """
    
    def __init__(
        self,
        atr_length: int = 14,
        hammer_fib: float = 33.0,
        doji_size: float = 5.0,
        shadow_percent: float = 5.0,
        min_size_atr: float = 0.1,
        max_size_atr: float = 0.0,
        long_shadow_ratio: float = 75.0,
        doji_wick_ratio: float = 2.0,
        engulf_wick: bool = False,
        color_match: bool = False,
        tweezer_half: bool = False,
    ):
        self.atr_length = atr_length
        self.hammer_fib = hammer_fib / 100.0
        self.doji_size = doji_size / 100.0
        self.shadow_percent = shadow_percent / 100.0
        self.min_size_atr = min_size_atr
        self.max_size_atr = max_size_atr
        self.long_shadow_ratio = long_shadow_ratio / 100.0
        self.doji_wick_ratio = doji_wick_ratio
        self.engulf_wick = engulf_wick
        self.color_match = color_match
        self.tweezer_half = tweezer_half
    
    def _calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """Calculate Average True Range."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=self.atr_length).mean()
        
        return atr
    
    def _bar_range(self, row: pd.Series) -> float:
        """Calculate the range of a candle (high - low)."""
        return row['high'] - row['low']
    
    def _body_size(self, row: pd.Series) -> float:
        """Calculate the body size of a candle."""
        return abs(row['close'] - row['open'])
    
    def _upper_wick(self, row: pd.Series) -> float:
        """Calculate the upper wick size."""
        return row['high'] - max(row['open'], row['close'])
    
    def _lower_wick(self, row: pd.Series) -> float:
        """Calculate the lower wick size."""
        return min(row['open'], row['close']) - row['low']
    
    def _is_bullish(self, row: pd.Series) -> bool:
        """Check if candle is bullish (close > open)."""
        return bool(row['close'] > row['open'])
    
    def _is_bearish(self, row: pd.Series) -> bool:
        """Check if candle is bearish (close < open)."""
        return bool(row['close'] < row['open'])
    
    def _passes_size_filter(self, bar_range: float, atr: float) -> bool:
        """Check if candle passes ATR-based size filter."""
        if atr == 0:
            return True
        
        min_check = bar_range >= self.min_size_atr * atr
        max_check = self.max_size_atr == 0 or bar_range <= self.max_size_atr * atr
        
        return min_check and max_check
    
    def _is_at_key_level(
        self,
        price: float,
        zones: Optional[List[Any]],
    ) -> tuple:
        """Check if price is within a key level zone."""
        if zones is None:
            return False, None
        
        for zone in zones:
            # Handle both Zone objects and dicts
            if hasattr(zone, 'top'):
                top, bottom = zone.top, zone.bottom
                zone_type = zone.zone_type.value if hasattr(zone.zone_type, 'value') else str(zone.zone_type)
            else:
                top, bottom = zone.get('top', 0), zone.get('bottom', 0)
                zone_type = zone.get('type', 'unknown')
            
            if bottom <= price <= top:
                return True, zone_type
        
        return False, None
    
    def _detect_doji(self, row: pd.Series, atr: float) -> bool:
        """
        Detect Doji pattern.
        
        Doji: body is very small relative to candle range,
        wicks are relatively balanced.
        """
        bar_range = self._bar_range(row)
        body = self._body_size(row)
        
        if bar_range == 0:
            return False
        
        body_ratio = body / bar_range
        
        if body_ratio > self.doji_size:
            return False
        
        # Check wick balance
        upper = self._upper_wick(row)
        lower = self._lower_wick(row)
        
        if lower == 0 and upper == 0:
            return body_ratio <= self.doji_size
        
        if lower == 0:
            wick_ratio = float('inf')
        else:
            wick_ratio = upper / lower if lower > 0 else float('inf')
        
        if upper == 0:
            wick_ratio = 0 if lower == 0 else 1 / (lower / upper if upper > 0 else float('inf'))
        
        max_ratio = self.doji_wick_ratio
        balanced = (1 / max_ratio) <= wick_ratio <= max_ratio if wick_ratio != float('inf') else False
        
        return body_ratio <= self.doji_size
    
    def _detect_hammer(self, row: pd.Series, atr: float) -> bool:
        """
        Detect Hammer pattern (bullish reversal).
        
        Hammer: small body at top, long lower wick, minimal upper wick.
        """
        bar_range = self._bar_range(row)
        body = self._body_size(row)
        lower = self._lower_wick(row)
        upper = self._upper_wick(row)
        
        if bar_range == 0:
            return False
        
        # Size filter
        if bar_range < self.min_size_atr * atr:
            return False
        
        body_ratio = body / bar_range
        upper_ratio = upper / body if body > 0 else float('inf')
        
        # Body must be small (hammer_fib)
        # Upper wick must be small relative to body
        # Color match optional
        is_hammer = (
            body_ratio <= self.hammer_fib and
            upper_ratio <= self.shadow_percent and
            lower > body * 2  # Lower wick should be at least 2x body
        )
        
        if self.color_match:
            is_hammer = is_hammer and self._is_bullish(row)
        
        return is_hammer
    
    def _detect_shooting_star(self, row: pd.Series, atr: float) -> bool:
        """
        Detect Shooting Star pattern (bearish reversal).
        
        Shooting Star: small body at bottom, long upper wick, minimal lower wick.
        """
        bar_range = self._bar_range(row)
        body = self._body_size(row)
        lower = self._lower_wick(row)
        upper = self._upper_wick(row)
        
        if bar_range == 0:
            return False
        
        # Size filter
        if bar_range < self.min_size_atr * atr:
            return False
        
        body_ratio = body / bar_range
        lower_ratio = lower / body if body > 0 else float('inf')
        
        is_star = (
            body_ratio <= self.hammer_fib and
            lower_ratio <= self.shadow_percent and
            upper > body * 2
        )
        
        if self.color_match:
            is_star = is_star and self._is_bearish(row)
        
        return is_star
    
    def _detect_dragonfly_doji(self, row: pd.Series, atr: float) -> bool:
        """
        Detect Dragonfly Doji (bullish).
        
        Dragonfly: doji with long lower wick, minimal upper wick.
        """
        bar_range = self._bar_range(row)
        body = self._body_size(row)
        lower = self._lower_wick(row)
        upper = self._upper_wick(row)
        
        if bar_range == 0:
            return False
        
        body_ratio = body / bar_range
        
        return (
            body_ratio <= self.doji_size and
            lower > bar_range * 0.6 and
            upper < bar_range * 0.1
        )
    
    def _detect_gravestone_doji(self, row: pd.Series, atr: float) -> bool:
        """
        Detect Gravestone Doji (bearish).
        
        Gravestone: doji with long upper wick, minimal lower wick.
        """
        bar_range = self._bar_range(row)
        body = self._body_size(row)
        lower = self._lower_wick(row)
        upper = self._upper_wick(row)
        
        if bar_range == 0:
            return False
        
        body_ratio = body / bar_range
        
        return (
            body_ratio <= self.doji_size and
            upper > bar_range * 0.6 and
            lower < bar_range * 0.1
        )
    
    def _detect_spinning_top(self, row: pd.Series, atr: float) -> bool:
        """
        Detect Spinning Top (indecision).
        
        Spinning Top: small body with upper and lower wicks.
        """
        bar_range = self._bar_range(row)
        body = self._body_size(row)
        lower = self._lower_wick(row)
        upper = self._upper_wick(row)
        
        if bar_range == 0:
            return False
        
        body_ratio = body / bar_range
        
        return (
            body_ratio <= 0.3 and  # Small body
            upper > body * 0.5 and  # Has upper wick
            lower > body * 0.5  # Has lower wick
        )
    
    def _detect_bullish_engulfing(
        self,
        curr: pd.Series,
        prev: pd.Series,
        atr: float,
    ) -> bool:
        """
        Detect Bullish Engulfing pattern.
        
        Previous candle bearish, current candle bullish and engulfs previous.
        """
        if not self._is_bearish(prev) or not self._is_bullish(curr):
            return False
        
        if self.engulf_wick:
            # Must engulf entire previous candle including wicks
            return curr['close'] > prev['high'] and curr['open'] < prev['low']
        else:
            # Must engulf previous body
            prev_body_top = max(prev['open'], prev['close'])
            prev_body_bottom = min(prev['open'], prev['close'])
            return curr['close'] > prev_body_top and curr['open'] < prev_body_bottom
    
    def _detect_bearish_engulfing(
        self,
        curr: pd.Series,
        prev: pd.Series,
        atr: float,
    ) -> bool:
        """
        Detect Bearish Engulfing pattern.
        
        Previous candle bullish, current candle bearish and engulfs previous.
        """
        if not self._is_bullish(prev) or not self._is_bearish(curr):
            return False
        
        if self.engulf_wick:
            return curr['open'] > prev['high'] and curr['close'] < prev['low']
        else:
            prev_body_top = max(prev['open'], prev['close'])
            prev_body_bottom = min(prev['open'], prev['close'])
            return curr['open'] > prev_body_top and curr['close'] < prev_body_bottom
    
    def _detect_tweezer_bottom(
        self,
        curr: pd.Series,
        prev: pd.Series,
        atr: float,
    ) -> bool:
        """
        Detect Tweezer Bottom pattern.
        
        Two candles with matching lows, second is bullish.
        """
        if not self._is_bullish(curr):
            return False
        
        # Lows should be very close (within 0.1% of price)
        low_tolerance = prev['low'] * 0.001
        matching_lows = abs(curr['low'] - prev['low']) <= low_tolerance
        
        if not matching_lows:
            return False
        
        if self.tweezer_half:
            # Current close should be above midpoint of previous candle
            prev_mid = (prev['high'] + prev['low']) / 2
            return curr['close'] > prev_mid
        
        return True
    
    def _detect_tweezer_top(
        self,
        curr: pd.Series,
        prev: pd.Series,
        atr: float,
    ) -> bool:
        """
        Detect Tweezer Top pattern.
        
        Two candles with matching highs, second is bearish.
        """
        if not self._is_bearish(curr):
            return False
        
        high_tolerance = prev['high'] * 0.001
        matching_highs = abs(curr['high'] - prev['high']) <= high_tolerance
        
        if not matching_highs:
            return False
        
        if self.tweezer_half:
            prev_mid = (prev['high'] + prev['low']) / 2
            return curr['close'] < prev_mid
        
        return True
    
    def _detect_piercing(
        self,
        curr: pd.Series,
        prev: pd.Series,
        atr: float,
    ) -> bool:
        """
        Detect Piercing pattern (bullish).
        
        Previous bearish, current opens below prev low, closes above prev midpoint.
        """
        if not self._is_bearish(prev) or not self._is_bullish(curr):
            return False
        
        prev_mid = (prev['open'] + prev['close']) / 2
        
        return (
            curr['open'] < prev['low'] and
            curr['close'] > prev_mid and
            curr['close'] < prev['open']  # But not a full engulfing
        )
    
    def _detect_dark_cloud_cover(
        self,
        curr: pd.Series,
        prev: pd.Series,
        atr: float,
    ) -> bool:
        """
        Detect Dark Cloud Cover pattern (bearish).
        
        Previous bullish, current opens above prev high, closes below prev midpoint.
        """
        if not self._is_bullish(prev) or not self._is_bearish(curr):
            return False
        
        prev_mid = (prev['open'] + prev['close']) / 2
        
        return (
            curr['open'] > prev['high'] and
            curr['close'] < prev_mid and
            curr['close'] > prev['close']  # But not a full engulfing
        )
    
    def _detect_bullish_harami(
        self,
        curr: pd.Series,
        prev: pd.Series,
        atr: float,
    ) -> bool:
        """
        Detect Bullish Harami pattern.
        
        Previous bearish large candle, current small bullish candle inside previous.
        """
        if not self._is_bearish(prev) or not self._is_bullish(curr):
            return False
        
        prev_body_top = prev['open']
        prev_body_bottom = prev['close']
        curr_body_top = curr['close']
        curr_body_bottom = curr['open']
        
        return (
            curr_body_top < prev_body_top and
            curr_body_bottom > prev_body_bottom and
            self._body_size(curr) < self._body_size(prev) * 0.5
        )
    
    def _detect_bearish_harami(
        self,
        curr: pd.Series,
        prev: pd.Series,
        atr: float,
    ) -> bool:
        """
        Detect Bearish Harami pattern.
        
        Previous bullish large candle, current small bearish candle inside previous.
        """
        if not self._is_bullish(prev) or not self._is_bearish(curr):
            return False
        
        prev_body_top = prev['close']
        prev_body_bottom = prev['open']
        curr_body_top = curr['open']
        curr_body_bottom = curr['close']
        
        return (
            curr_body_top < prev_body_top and
            curr_body_bottom > prev_body_bottom and
            self._body_size(curr) < self._body_size(prev) * 0.5
        )
    
    def _detect_long_lower_shadow(self, row: pd.Series, atr: float) -> bool:
        """
        Detect Long Lower Shadow pattern (bullish).
        
        Candle with exceptionally long lower wick relative to body.
        """
        bar_range = self._bar_range(row)
        lower = self._lower_wick(row)
        
        if bar_range == 0:
            return False
        
        # Size filter
        if bar_range < self.min_size_atr * atr:
            return False
        
        lower_ratio = lower / bar_range
        
        return lower_ratio >= self.long_shadow_ratio
    
    def _detect_long_upper_shadow(self, row: pd.Series, atr: float) -> bool:
        """
        Detect Long Upper Shadow pattern (bearish).
        
        Candle with exceptionally long upper wick relative to body.
        """
        bar_range = self._bar_range(row)
        upper = self._upper_wick(row)
        
        if bar_range == 0:
            return False
        
        # Size filter
        if bar_range < self.min_size_atr * atr:
            return False
        
        upper_ratio = upper / bar_range
        
        return upper_ratio >= self.long_shadow_ratio
    
    def scan(
        self,
        df: pd.DataFrame,
        zones: Optional[List[Any]] = None,
        only_at_levels: bool = False,
        lookback: int = 50,
    ) -> List[PatternMatch]:
        """
        Scan for candlestick patterns in OHLCV data.
        
        Args:
            df: DataFrame with columns: open, high, low, close
            zones: Optional list of Zone objects or dicts for key level filtering
            only_at_levels: If True, only return patterns at key levels
            lookback: Number of bars to scan (from end of DataFrame)
        
        Returns:
            List of PatternMatch objects for detected patterns
        """
        patterns = []
        
        # Validate input
        required_cols = ['open', 'high', 'low', 'close']
        df = df.copy()
        df.columns = df.columns.str.lower()
        
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"DataFrame missing required columns: {missing}")
        
        if len(df) < 2:
            return patterns
        
        # Calculate ATR
        atr = self._calculate_atr(df)
        
        # Scan last `lookback` bars
        start_idx = max(1, len(df) - lookback)
        
        for i in range(start_idx, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i - 1]
            bar_atr = atr.iloc[i] if not pd.isna(atr.iloc[i]) else atr.mean()
            
            # Skip if doesn't pass size filter
            bar_range = self._bar_range(row)
            if self.max_size_atr > 0 and bar_range > self.max_size_atr * bar_atr:
                continue
            
            price = row['close']
            at_level, zone_type = self._is_at_key_level(price, zones)
            
            # Skip if only_at_levels and not at a key level
            if only_at_levels and not at_level:
                continue
            
            # Single-bar patterns
            single_bar_checks = [
                (self._detect_doji, PatternType.DOJI),
                (self._detect_hammer, PatternType.HAMMER),
                (self._detect_shooting_star, PatternType.SHOOTING_STAR),
                (self._detect_dragonfly_doji, PatternType.DRAGONFLY_DOJI),
                (self._detect_gravestone_doji, PatternType.GRAVESTONE_DOJI),
                (self._detect_spinning_top, PatternType.SPINNING_TOP),
                (self._detect_long_lower_shadow, PatternType.LONG_LOWER_SHADOW),
                (self._detect_long_upper_shadow, PatternType.LONG_UPPER_SHADOW),
            ]
            
            for check_func, pattern_type in single_bar_checks:
                if check_func(row, bar_atr):
                    direction = PATTERN_DIRECTION[pattern_type]
                    confidence = 0.8 if at_level else 0.5
                    
                    patterns.append(PatternMatch(
                        pattern_type=pattern_type,
                        direction=direction,
                        bar_index=i,
                        price=price,
                        confidence=confidence,
                        at_key_level=at_level,
                        zone_type=zone_type,
                        pattern_bars=1,
                    ))
            
            # Two-bar patterns
            two_bar_checks = [
                (self._detect_bullish_engulfing, PatternType.BULLISH_ENGULFING),
                (self._detect_bearish_engulfing, PatternType.BEARISH_ENGULFING),
                (self._detect_tweezer_bottom, PatternType.TWEEZER_BOTTOM),
                (self._detect_tweezer_top, PatternType.TWEEZER_TOP),
                (self._detect_piercing, PatternType.PIERCING),
                (self._detect_dark_cloud_cover, PatternType.DARK_CLOUD_COVER),
                (self._detect_bullish_harami, PatternType.BULLISH_HARAMI),
                (self._detect_bearish_harami, PatternType.BEARISH_HARAMI),
            ]
            
            for check_func, pattern_type in two_bar_checks:
                if check_func(row, prev_row, bar_atr):
                    direction = PATTERN_DIRECTION[pattern_type]
                    confidence = 0.85 if at_level else 0.55
                    
                    patterns.append(PatternMatch(
                        pattern_type=pattern_type,
                        direction=direction,
                        bar_index=i,
                        price=price,
                        confidence=confidence,
                        at_key_level=at_level,
                        zone_type=zone_type,
                        pattern_bars=2,
                    ))
        
        return patterns
    
    def scan_latest(
        self,
        df: pd.DataFrame,
        zones: Optional[List[Any]] = None,
        only_at_levels: bool = False,
    ) -> List[PatternMatch]:
        """
        Scan only the latest candle for patterns.
        
        Optimized for real-time detection.
        """
        return self.scan(df, zones, only_at_levels, lookback=1)


# ============================================================================
# Tool Function for Agent Integration
# ============================================================================

def scan_candle_patterns(
    symbol: Annotated[str, "Trading pair symbol (e.g., 'BTCUSDT', 'ETHUSDT')"],
    interval: Annotated[str, "Timeframe interval (e.g., '1H', '4H', '1D')"] = "1H",
    only_at_levels: Annotated[bool, "Only detect patterns at Key S/R Levels"] = True,
    bars: Annotated[int, "Number of bars to analyze (default: 200)"] = 200,
    lookback: Annotated[int, "Number of bars to scan for patterns (default: 50)"] = 50,
) -> str:
    """
    Scan for candlestick patterns, optionally filtered to Key Levels only.
    
    Detects 16 pattern types including Hammer, Engulfing, Doji, etc.
    When only_at_levels=True, only patterns occurring at S/R zones are returned.
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT', 'ETHUSDT')
        interval: Timeframe interval (e.g., '1H', '4H', '1D')
        only_at_levels: Only detect patterns at Key S/R Levels
        bars: Number of bars to analyze
        lookback: Number of bars to scan for patterns
    
    Returns:
        JSON string with detected patterns
    """
    try:
        from exchange_tools import get_ohlcv_data
        from keylevel_analyzer import KeyLevelAnalyzer
        
        # Fetch OHLCV data
        ohlcv_json = get_ohlcv_data(symbol=symbol, interval=interval, limit=bars)
        ohlcv_data = json.loads(ohlcv_json)
        
        if "error" in ohlcv_data:
            return json.dumps({"error": ohlcv_data["error"]})
        
        candles = ohlcv_data.get("candles", [])
        if not candles:
            return json.dumps({"error": "No candle data returned"})
        
        df = pd.DataFrame(candles)
        
        # Get key levels if filtering by levels
        zones = None
        if only_at_levels:
            analyzer = KeyLevelAnalyzer()
            key_level_result = analyzer.analyze(df)
            zones = [z.to_dict() for z in key_level_result.zones]
        
        # Scan for patterns
        scanner = CandlePatternScanner()
        patterns = scanner.scan(df, zones=zones, only_at_levels=only_at_levels, lookback=lookback)
        
        # Group by direction
        bullish = [p.to_dict() for p in patterns if p.direction == PatternDirection.BULLISH]
        bearish = [p.to_dict() for p in patterns if p.direction == PatternDirection.BEARISH]
        neutral = [p.to_dict() for p in patterns if p.direction == PatternDirection.NEUTRAL]
        
        output = {
            "symbol": symbol,
            "interval": interval,
            "bars_analyzed": len(df),
            "only_at_levels": only_at_levels,
            "patterns_found": len(patterns),
            "bullish_patterns": bullish,
            "bearish_patterns": bearish,
            "neutral_patterns": neutral,
            "current_price": float(df['close'].iloc[-1]),
        }
        
        # Add signal summary
        if len(bullish) > len(bearish):
            output["bias"] = "BULLISH"
            output["signal"] = f"{len(bullish)} bullish vs {len(bearish)} bearish patterns"
        elif len(bearish) > len(bullish):
            output["bias"] = "BEARISH"
            output["signal"] = f"{len(bearish)} bearish vs {len(bullish)} bullish patterns"
        else:
            output["bias"] = "NEUTRAL"
            output["signal"] = "Equal bullish and bearish patterns"
        
        return json.dumps(output, indent=2)
    
    except Exception as e:
        logger.error(f"Error scanning candle patterns: {e}")
        return json.dumps({"error": str(e)})


def get_latest_pattern(
    symbol: Annotated[str, "Trading pair symbol (e.g., 'BTCUSDT', 'ETHUSDT')"],
    interval: Annotated[str, "Timeframe interval (e.g., '1H', '4H')"] = "1H",
) -> str:
    """
    Get the latest candlestick pattern on the current bar.
    
    Optimized for real-time pattern detection alerts.
    
    Args:
        symbol: Trading pair symbol
        interval: Timeframe interval
    
    Returns:
        JSON string with latest pattern info
    """
    try:
        from exchange_tools import get_ohlcv_data
        from keylevel_analyzer import KeyLevelAnalyzer
        
        ohlcv_json = get_ohlcv_data(symbol=symbol, interval=interval, limit=100)
        ohlcv_data = json.loads(ohlcv_json)
        
        if "error" in ohlcv_data:
            return json.dumps({"error": ohlcv_data["error"]})
        
        candles = ohlcv_data.get("candles", [])
        if not candles:
            return json.dumps({"error": "No candle data returned"})
        
        df = pd.DataFrame(candles)
        
        # Get key levels
        analyzer = KeyLevelAnalyzer()
        key_level_result = analyzer.analyze(df)
        zones = [z.to_dict() for z in key_level_result.zones]
        
        # Scan latest bar
        scanner = CandlePatternScanner()
        patterns = scanner.scan_latest(df, zones=zones, only_at_levels=False)
        
        if patterns:
            latest = patterns[-1]
            output = {
                "symbol": symbol,
                "interval": interval,
                "has_pattern": True,
                "pattern": latest.to_dict(),
                "current_price": float(df['close'].iloc[-1]),
            }
        else:
            output = {
                "symbol": symbol,
                "interval": interval,
                "has_pattern": False,
                "pattern": None,
                "current_price": float(df['close'].iloc[-1]),
            }
        
        return json.dumps(output, indent=2)
    
    except Exception as e:
        logger.error(f"Error getting latest pattern: {e}")
        return json.dumps({"error": str(e)})
