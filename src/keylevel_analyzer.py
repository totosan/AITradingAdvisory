"""
KeyLevel Analyzer for AITradingAdvisory

Ported from Bjorgum Key Levels PineScript indicator.
Detects Support/Resistance zones using pivot-based analysis with:
- Pivot High/Low detection (look-left/look-right)
- ATR-normalized zone width
- Zone merging for overlapping levels
- False break (bull/bear trap) detection
- Heiken Ashi smoothing for cleaner pivots

Usage:
    analyzer = KeyLevelAnalyzer(left=20, right=15)
    result = analyzer.analyze(df)  # df with OHLCV columns
    print(result)  # JSON output with zones, current_position, false_breaks, breakout_status
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Annotated, Optional, List, Dict, Any, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class ZoneType(Enum):
    """Type of support/resistance zone."""
    SUPPORT = "support"
    RESISTANCE = "resistance"


@dataclass
class Zone:
    """
    Represents a Support/Resistance zone.
    
    Attributes:
        top: Upper boundary of the zone
        bottom: Lower boundary of the zone
        zone_type: SUPPORT or RESISTANCE
        strength: Number of times price has touched/merged at this level
        created_bar: Bar index when the zone was first created
        is_bull: True if price closed above the zone (flipped to support)
        last_test_bar: Last bar index where price tested this zone
    """
    top: float
    bottom: float
    zone_type: ZoneType
    strength: int = 1
    created_bar: int = 0
    is_bull: bool = True
    last_test_bar: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "top": float(self.top),
            "bottom": float(self.bottom),
            "type": self.zone_type.value,
            "strength": int(self.strength),
            "created_bar": int(self.created_bar),
            "is_bull": bool(self.is_bull),
            "last_test_bar": int(self.last_test_bar) if self.last_test_bar is not None else None,
        }
    
    def overlaps(self, other: "Zone") -> bool:
        """Check if this zone overlaps with another zone."""
        # From PineScript: if _T > _b and _T < _t or _B < _t and _B > _b
        return (
            (other.top > self.bottom and other.top < self.top) or
            (other.bottom < self.top and other.bottom > self.bottom) or
            (other.top > self.top and other.bottom < self.bottom) or
            (other.bottom > self.bottom and other.top < self.top)
        )
    
    def merge_with(self, other: "Zone") -> "Zone":
        """Merge this zone with another overlapping zone."""
        return Zone(
            top=max(self.top, other.top),
            bottom=min(self.bottom, other.bottom),
            zone_type=self.zone_type,
            strength=self.strength + other.strength,
            created_bar=min(self.created_bar, other.created_bar),
            is_bull=self.is_bull,
            last_test_bar=max(
                self.last_test_bar or 0,
                other.last_test_bar or 0
            ) or None,
        )


@dataclass
class FalseBreak:
    """Represents a false break (bull/bear trap) detection."""
    type: str  # "false_breakdown" or "false_breakup"
    bar_index: int
    zone_top: float
    zone_bottom: float
    price: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "bar_index": int(self.bar_index),
            "zone_top": float(self.zone_top),
            "zone_bottom": float(self.zone_bottom),
            "price": float(self.price),
        }


@dataclass
class CurrentPosition:
    """Current price position relative to zones."""
    in_zone: bool
    zone_type: Optional[str]
    nearest_resistance: Optional[float]
    nearest_support: Optional[float]
    distance_to_resistance: Optional[float]
    distance_to_support: Optional[float]
    zones_above: int
    zones_below: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "in_zone": bool(self.in_zone),
            "zone_type": self.zone_type,
            "nearest_resistance": float(self.nearest_resistance) if self.nearest_resistance is not None else None,
            "nearest_support": float(self.nearest_support) if self.nearest_support is not None else None,
            "distance_to_resistance": float(self.distance_to_resistance) if self.distance_to_resistance is not None else None,
            "distance_to_support": float(self.distance_to_support) if self.distance_to_support is not None else None,
            "zones_above": int(self.zones_above),
            "zones_below": int(self.zones_below),
        }


@dataclass
class BreakoutStatus:
    """Status of potential breakout."""
    is_breakout: bool
    direction: Optional[str]  # "up", "down", or None
    zones_broken: int
    breakout_price: Optional[float]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_breakout": bool(self.is_breakout),
            "direction": self.direction,
            "zones_broken": int(self.zones_broken),
            "breakout_price": float(self.breakout_price) if self.breakout_price is not None else None,
        }


@dataclass
class KeyLevelAnalysis:
    """Complete analysis result from KeyLevelAnalyzer."""
    zones: List[Zone]
    current_position: CurrentPosition
    false_breaks: List[FalseBreak]
    breakout_status: BreakoutStatus
    range_info: Optional[Dict[str, float]] = None
    atr_value: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "zones": [z.to_dict() for z in self.zones],
            "current_position": self.current_position.to_dict(),
            "false_breaks": [fb.to_dict() for fb in self.false_breaks],
            "breakout_status": self.breakout_status.to_dict(),
            "range_info": self.range_info,
            "atr_value": float(self.atr_value),
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class KeyLevelAnalyzer:
    """
    Detects Support/Resistance zones from OHLCV data.
    
    Ported from Bjorgum Key Levels PineScript with the following features:
    - Pivot High/Low detection with configurable look-left/look-right
    - ATR-normalized zone width (zone = pivot ± ATR * mult)
    - Zone merging for overlapping levels (increases strength)
    - False break detection (bull/bear traps)
    - Heiken Ashi body calculation for smoother pivots
    
    Args:
        left: Look-left period for pivot detection (default: 20)
        right: Look-right period for pivot detection (default: 15)
        num_pivots: Maximum number of pivot zones to track (default: 4)
        atr_length: ATR calculation period (default: 30)
        zone_atr_mult: Zone width as ATR multiplier (default: 0.5)
        max_zone_percent: Maximum zone size as % of price (default: 5.0)
        use_heiken_ashi: Use HA bodies for pivot detection (default: True)
        merge_zones: Enable zone merging (default: True)
        false_break_lookback: Bars to look back for false breaks (default: 2)
    """
    
    def __init__(
        self,
        left: int = 20,
        right: int = 15,
        num_pivots: int = 4,
        atr_length: int = 30,
        zone_atr_mult: float = 0.5,
        max_zone_percent: float = 5.0,
        use_heiken_ashi: bool = True,
        merge_zones: bool = True,
        false_break_lookback: int = 2,
    ):
        self.left = left
        self.right = right
        self.num_pivots = num_pivots
        self.atr_length = atr_length
        self.zone_atr_mult = zone_atr_mult
        self.max_zone_percent = max_zone_percent
        self.use_heiken_ashi = use_heiken_ashi
        self.merge_zones = merge_zones
        self.false_break_lookback = false_break_lookback
    
    def _calculate_heiken_ashi(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate Heiken Ashi open and close values.
        
        HA Close = (Open + High + Low + Close) / 4
        HA Open = (Previous HA Open + Previous HA Close) / 2
        
        Returns:
            Tuple of (ha_open, ha_close) series
        """
        ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        
        ha_open = pd.Series(index=df.index, dtype=float)
        ha_open.iloc[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
        
        for i in range(1, len(df)):
            ha_open.iloc[i] = (ha_open.iloc[i-1] + ha_close.iloc[i-1]) / 2
        
        return ha_open, ha_close
    
    def _calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate Average True Range (ATR).
        
        True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
        ATR = EMA(True Range, atr_length)
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.ewm(span=self.atr_length, adjust=False).mean()
        
        return atr
    
    def _detect_pivots(
        self,
        df: pd.DataFrame,
        src_high: pd.Series,
        src_low: pd.Series,
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Detect pivot highs and lows using look-left/look-right method.
        
        A pivot high occurs when the price at bar[right] is the highest
        in the range [bar - left - right, bar].
        
        Returns:
            Tuple of (pivot_highs, pivot_lows) as lists of dicts with 'bar' and 'price'
        """
        pivot_highs = []
        pivot_lows = []
        
        n = len(df)
        
        # We need at least left + right + 1 bars
        if n < self.left + self.right + 1:
            return pivot_highs, pivot_lows
        
        for i in range(self.left + self.right, n):
            pivot_bar = i - self.right
            
            # Check for pivot high
            is_pivot_high = True
            pivot_high_price = src_high.iloc[pivot_bar]
            
            # Check left side
            for j in range(pivot_bar - self.left, pivot_bar):
                if j >= 0 and src_high.iloc[j] > pivot_high_price:
                    is_pivot_high = False
                    break
            
            # Check right side
            if is_pivot_high:
                for j in range(pivot_bar + 1, pivot_bar + self.right + 1):
                    if j < n and src_high.iloc[j] >= pivot_high_price:
                        is_pivot_high = False
                        break
            
            if is_pivot_high:
                pivot_highs.append({
                    'bar': pivot_bar,
                    'price': pivot_high_price,
                })
            
            # Check for pivot low
            is_pivot_low = True
            pivot_low_price = src_low.iloc[pivot_bar]
            
            # Check left side
            for j in range(pivot_bar - self.left, pivot_bar):
                if j >= 0 and src_low.iloc[j] < pivot_low_price:
                    is_pivot_low = False
                    break
            
            # Check right side
            if is_pivot_low:
                for j in range(pivot_bar + 1, pivot_bar + self.right + 1):
                    if j < n and src_low.iloc[j] <= pivot_low_price:
                        is_pivot_low = False
                        break
            
            if is_pivot_low:
                pivot_lows.append({
                    'bar': pivot_bar,
                    'price': pivot_low_price,
                })
        
        return pivot_highs, pivot_lows
    
    def _create_zones(
        self,
        pivot_highs: List[Dict],
        pivot_lows: List[Dict],
        atr: pd.Series,
        df: pd.DataFrame,
    ) -> List[Zone]:
        """
        Create zones from pivot points with ATR-normalized width.
        
        Zone width = min(ATR * mult, price * max_percent / 100) / 2
        Zone = [pivot - band, pivot + band]
        """
        zones = []
        current_price = df['close'].iloc[-1]
        
        # Process pivot highs (initial resistance zones)
        for pivot in pivot_highs[-self.num_pivots:]:
            bar_idx = pivot['bar']
            price = pivot['price']
            
            # Get ATR at the pivot bar (with right offset as in PineScript)
            atr_val = atr.iloc[bar_idx] if bar_idx < len(atr) else atr.iloc[-1]
            
            # Calculate band width: min(atr * mult, price * percent / 100) / 2
            max_band = price * (self.max_zone_percent / 100)
            band = min(atr_val * self.zone_atr_mult, max_band) / 2
            
            # Determine if zone is now support or resistance based on current price
            is_bull = current_price > price + band
            zone_type = ZoneType.SUPPORT if is_bull else ZoneType.RESISTANCE
            
            zones.append(Zone(
                top=price + band,
                bottom=price - band,
                zone_type=zone_type,
                strength=1,
                created_bar=bar_idx,
                is_bull=is_bull,
            ))
        
        # Process pivot lows (initial support zones)
        for pivot in pivot_lows[-self.num_pivots:]:
            bar_idx = pivot['bar']
            price = pivot['price']
            
            atr_val = atr.iloc[bar_idx] if bar_idx < len(atr) else atr.iloc[-1]
            max_band = price * (self.max_zone_percent / 100)
            band = min(atr_val * self.zone_atr_mult, max_band) / 2
            
            is_bull = current_price > price - band
            zone_type = ZoneType.SUPPORT if is_bull else ZoneType.RESISTANCE
            
            zones.append(Zone(
                top=price + band,
                bottom=price - band,
                zone_type=zone_type,
                strength=1,
                created_bar=bar_idx,
                is_bull=is_bull,
            ))
        
        return zones
    
    def _merge_overlapping_zones(self, zones: List[Zone]) -> List[Zone]:
        """
        Merge overlapping zones to create stronger levels.
        
        From PineScript _align() function:
        if _T > _b and _T < _t or _B < _t and _B > _b or _T > _t and _B < _b or _B > _b and _T < _t:
            merge zones
        """
        if not zones:
            return zones
        
        # Sort zones by bottom price
        sorted_zones = sorted(zones, key=lambda z: z.bottom)
        merged = [sorted_zones[0]]
        
        for zone in sorted_zones[1:]:
            last_merged = merged[-1]
            
            if zone.overlaps(last_merged):
                # Merge zones
                merged[-1] = last_merged.merge_with(zone)
            else:
                merged.append(zone)
        
        return merged
    
    def _update_zone_types(self, zones: List[Zone], current_price: float) -> List[Zone]:
        """
        Update zone types based on current price position.
        
        From PineScript _color() function:
        - If price closes above zone top and zone was resistance → flip to support
        - If price closes below zone bottom and zone was support → flip to resistance
        """
        for zone in zones:
            if current_price > zone.top and not zone.is_bull:
                zone.is_bull = True
                zone.zone_type = ZoneType.SUPPORT
            elif current_price < zone.bottom and zone.is_bull:
                zone.is_bull = False
                zone.zone_type = ZoneType.RESISTANCE
        
        return zones
    
    def _detect_false_breaks(
        self,
        df: pd.DataFrame,
        zones: List[Zone],
    ) -> List[FalseBreak]:
        """
        Detect false breaks (bull/bear traps).
        
        From PineScript _falseBreak() function:
        for i = 1 to lookback
            if _l[i] < _l and _l[i+1] >= _l and _l[1] < _l 
                false_breakdown detected
            if _l[i] > _l and _l[i+1] <= _l and _l[1] > _l 
                false_breakup detected
        
        Translation: A false breakdown occurs when:
        - Price broke below a level recently (within lookback)
        - Price has now recovered above that level
        - This is a "bear trap" - looks bearish but reverses bullish
        """
        false_breaks = []
        n = len(df)
        
        if n < self.false_break_lookback + 2:
            return false_breaks
        
        current_bar = n - 1
        current_close = df['close'].iloc[-1]
        current_low = df['low'].iloc[-1]
        current_high = df['high'].iloc[-1]
        
        for zone in zones:
            # Check for false breakdown (price broke below support, then recovered)
            # This is a bullish signal (bear trap)
            for i in range(1, self.false_break_lookback + 1):
                if current_bar - i - 1 < 0:
                    continue
                
                prev_low = df['low'].iloc[current_bar - i]
                prev_prev_low = df['low'].iloc[current_bar - i - 1]
                recent_low = df['low'].iloc[current_bar - 1]
                
                # False breakdown: went below zone, then recovered
                if (prev_low < zone.bottom and 
                    prev_prev_low >= zone.bottom and 
                    current_low >= zone.bottom and
                    current_close > zone.bottom):
                    false_breaks.append(FalseBreak(
                        type="false_breakdown",
                        bar_index=current_bar,
                        zone_top=zone.top,
                        zone_bottom=zone.bottom,
                        price=current_close,
                    ))
                    break
            
            # Check for false breakup (price broke above resistance, then failed)
            # This is a bearish signal (bull trap)
            for i in range(1, self.false_break_lookback + 1):
                if current_bar - i - 1 < 0:
                    continue
                
                prev_high = df['high'].iloc[current_bar - i]
                prev_prev_high = df['high'].iloc[current_bar - i - 1]
                recent_high = df['high'].iloc[current_bar - 1]
                
                # False breakup: went above zone, then failed
                if (prev_high > zone.top and 
                    prev_prev_high <= zone.top and 
                    current_high <= zone.top and
                    current_close < zone.top):
                    false_breaks.append(FalseBreak(
                        type="false_breakup",
                        bar_index=current_bar,
                        zone_top=zone.top,
                        zone_bottom=zone.bottom,
                        price=current_close,
                    ))
                    break
        
        return false_breaks
    
    def _detect_breakout(
        self,
        df: pd.DataFrame,
        zones: List[Zone],
    ) -> BreakoutStatus:
        """
        Detect if price has broken out above/below all zones.
        
        From PineScript:
        breakOut = moveAbove and highest and above == total
        breakDwn = moveBelow and lowest and above == 0
        
        A breakout occurs when:
        - Price is above ALL zone tops (bullish breakout)
        - Price is below ALL zone bottoms (bearish breakdown)
        """
        if not zones:
            return BreakoutStatus(
                is_breakout=False,
                direction=None,
                zones_broken=0,
                breakout_price=None,
            )
        
        current_price = df['close'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        
        zones_above = sum(1 for z in zones if z.is_bull)
        total_zones = len(zones)
        
        # Check for bullish breakout (above all zones)
        all_above = all(current_price > zone.top for zone in zones)
        if all_above and zones_above == total_zones:
            return BreakoutStatus(
                is_breakout=True,
                direction="up",
                zones_broken=total_zones,
                breakout_price=current_price,
            )
        
        # Check for bearish breakdown (below all zones)
        all_below = all(current_price < zone.bottom for zone in zones)
        if all_below and zones_above == 0:
            return BreakoutStatus(
                is_breakout=True,
                direction="down",
                zones_broken=total_zones,
                breakout_price=current_price,
            )
        
        # Count how many zones price has broken through
        zones_broken_up = sum(1 for z in zones if current_price > z.top)
        zones_broken_down = sum(1 for z in zones if current_price < z.bottom)
        
        return BreakoutStatus(
            is_breakout=False,
            direction=None,
            zones_broken=max(zones_broken_up, zones_broken_down),
            breakout_price=None,
        )
    
    def _calculate_current_position(
        self,
        current_price: float,
        zones: List[Zone],
    ) -> CurrentPosition:
        """Calculate current price position relative to zones."""
        in_zone = False
        zone_type = None
        nearest_resistance = None
        nearest_support = None
        zones_above = 0
        zones_below = 0
        
        for zone in zones:
            # Check if price is inside this zone
            if zone.bottom <= current_price <= zone.top:
                in_zone = True
                zone_type = zone.zone_type.value
            
            # Count zones above and below
            if zone.bottom > current_price:
                zones_above += 1
                # Track nearest resistance
                if nearest_resistance is None or zone.bottom < nearest_resistance:
                    nearest_resistance = zone.bottom
            elif zone.top < current_price:
                zones_below += 1
                # Track nearest support
                if nearest_support is None or zone.top > nearest_support:
                    nearest_support = zone.top
        
        # Calculate distances
        distance_to_resistance = None
        distance_to_support = None
        
        if nearest_resistance is not None:
            distance_to_resistance = (nearest_resistance - current_price) / current_price
        
        if nearest_support is not None:
            distance_to_support = (current_price - nearest_support) / current_price
        
        return CurrentPosition(
            in_zone=in_zone,
            zone_type=zone_type,
            nearest_resistance=nearest_resistance,
            nearest_support=nearest_support,
            distance_to_resistance=distance_to_resistance,
            distance_to_support=distance_to_support,
            zones_above=zones_above,
            zones_below=zones_below,
        )
    
    def _calculate_range_info(
        self,
        zones: List[Zone],
        current_price: float,
    ) -> Optional[Dict[str, float]]:
        """
        Calculate range information if price is ranging between zones.
        
        Returns range high/low if there are zones both above and below current price.
        """
        resistance_zones = [z for z in zones if z.bottom > current_price]
        support_zones = [z for z in zones if z.top < current_price]
        
        if resistance_zones and support_zones:
            range_high = min(z.bottom for z in resistance_zones)
            range_low = max(z.top for z in support_zones)
            range_size = range_high - range_low
            range_percent = (range_size / current_price) * 100
            
            return {
                "high": round(range_high, 2),
                "low": round(range_low, 2),
                "size": round(range_size, 2),
                "percent": round(range_percent, 2),
            }
        
        return None
    
    def analyze(self, df: pd.DataFrame) -> KeyLevelAnalysis:
        """
        Perform complete Key Level analysis on OHLCV data.
        
        Args:
            df: DataFrame with columns: open, high, low, close, volume
                Index should be datetime or integer
        
        Returns:
            KeyLevelAnalysis with zones, current_position, false_breaks, breakout_status
        """
        # Validate input
        required_cols = ['open', 'high', 'low', 'close']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"DataFrame missing required columns: {missing}")
        
        if len(df) < self.left + self.right + 1:
            logger.warning(f"DataFrame too short ({len(df)} bars) for pivot detection")
            return KeyLevelAnalysis(
                zones=[],
                current_position=CurrentPosition(
                    in_zone=False,
                    zone_type=None,
                    nearest_resistance=None,
                    nearest_support=None,
                    distance_to_resistance=None,
                    distance_to_support=None,
                    zones_above=0,
                    zones_below=0,
                ),
                false_breaks=[],
                breakout_status=BreakoutStatus(
                    is_breakout=False,
                    direction=None,
                    zones_broken=0,
                    breakout_price=None,
                ),
            )
        
        # Normalize column names to lowercase
        df = df.copy()
        df.columns = df.columns.str.lower()
        
        # Calculate ATR
        atr = self._calculate_atr(df)
        current_atr = atr.iloc[-1]
        
        # Calculate source for pivot detection
        if self.use_heiken_ashi:
            ha_open, ha_close = self._calculate_heiken_ashi(df)
            src_high = pd.concat([ha_open, ha_close], axis=1).max(axis=1)
            src_low = pd.concat([ha_open, ha_close], axis=1).min(axis=1)
        else:
            # Use body highs/lows
            src_high = pd.concat([df['open'], df['close']], axis=1).max(axis=1)
            src_low = pd.concat([df['open'], df['close']], axis=1).min(axis=1)
        
        # Detect pivots
        pivot_highs, pivot_lows = self._detect_pivots(df, src_high, src_low)
        
        # Create zones from pivots
        zones = self._create_zones(pivot_highs, pivot_lows, atr, df)
        
        # Merge overlapping zones
        if self.merge_zones:
            zones = self._merge_overlapping_zones(zones)
        
        # Update zone types based on current price
        current_price = df['close'].iloc[-1]
        zones = self._update_zone_types(zones, current_price)
        
        # Detect false breaks
        false_breaks = self._detect_false_breaks(df, zones)
        
        # Detect breakout status
        breakout_status = self._detect_breakout(df, zones)
        
        # Calculate current position
        current_position = self._calculate_current_position(current_price, zones)
        
        # Calculate range info
        range_info = self._calculate_range_info(zones, current_price)
        
        return KeyLevelAnalysis(
            zones=zones,
            current_position=current_position,
            false_breaks=false_breaks,
            breakout_status=breakout_status,
            range_info=range_info,
            atr_value=current_atr,
        )


# ============================================================================
# Tool Function for Agent Integration
# ============================================================================

# Global analyzer instance (can be customized per request if needed)
_default_analyzer = KeyLevelAnalyzer()


def analyze_key_levels(
    symbol: Annotated[str, "Trading pair symbol (e.g., 'BTCUSDT', 'ETHUSDT')"],
    interval: Annotated[str, "Timeframe interval (e.g., '1H', '4H', '1D')"] = "1H",
    bars: Annotated[int, "Number of bars to analyze (default: 200)"] = 200,
    left: Annotated[int, "Look-left period for pivot detection (default: 20)"] = 20,
    right: Annotated[int, "Look-right period for pivot detection (default: 15)"] = 15,
    zone_atr_mult: Annotated[float, "Zone width as ATR multiplier (default: 0.5)"] = 0.5,
) -> str:
    """
    Analyze Key Levels (Support/Resistance) for a trading pair.
    
    Detects pivot-based S/R zones, false breaks (bull/bear traps),
    and breakout conditions. Ported from Bjorgum Key Levels PineScript.
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT', 'ETHUSDT')
        interval: Timeframe interval (e.g., '1H', '4H', '1D')
        bars: Number of bars to analyze
        left: Look-left period for pivot detection
        right: Look-right period for pivot detection
        zone_atr_mult: Zone width as ATR multiplier
    
    Returns:
        JSON string with zones, current_position, false_breaks, breakout_status
    """
    try:
        # Import exchange tools to get OHLCV data
        from exchange_tools import get_ohlcv_data
        
        # Fetch OHLCV data
        ohlcv_json = get_ohlcv_data(symbol=symbol, interval=interval, limit=bars)
        ohlcv_data = json.loads(ohlcv_json)
        
        if "error" in ohlcv_data:
            return json.dumps({"error": ohlcv_data["error"]})
        
        # Convert to DataFrame
        candles = ohlcv_data.get("candles", [])
        if not candles:
            return json.dumps({"error": "No candle data returned"})
        
        df = pd.DataFrame(candles)
        
        # Create analyzer with custom parameters
        analyzer = KeyLevelAnalyzer(
            left=left,
            right=right,
            zone_atr_mult=zone_atr_mult,
        )
        
        # Perform analysis
        result = analyzer.analyze(df)
        
        # Add metadata
        output = result.to_dict()
        output["symbol"] = symbol
        output["interval"] = interval
        output["bars_analyzed"] = len(df)
        output["current_price"] = float(df['close'].iloc[-1])
        
        return json.dumps(output, indent=2)
    
    except Exception as e:
        logger.error(f"Error analyzing key levels: {e}")
        return json.dumps({"error": str(e)})


def detect_false_break(
    symbol: Annotated[str, "Trading pair symbol (e.g., 'BTCUSDT', 'ETHUSDT')"],
    interval: Annotated[str, "Timeframe interval (e.g., '1H', '4H')"] = "1H",
    lookback: Annotated[int, "Bars to look back for false break detection (default: 2)"] = 2,
) -> str:
    """
    Detect false breaks (bull/bear traps) at key levels.
    
    A false break occurs when price briefly breaks a support/resistance
    level but quickly reverses. These are often powerful trading signals.
    
    Args:
        symbol: Trading pair symbol
        interval: Timeframe interval
        lookback: Bars to look back for false break detection
    
    Returns:
        JSON string with false break detections
    """
    try:
        from exchange_tools import get_ohlcv_data
        
        ohlcv_json = get_ohlcv_data(symbol=symbol, interval=interval, limit=200)
        ohlcv_data = json.loads(ohlcv_json)
        
        if "error" in ohlcv_data:
            return json.dumps({"error": ohlcv_data["error"]})
        
        candles = ohlcv_data.get("candles", [])
        if not candles:
            return json.dumps({"error": "No candle data returned"})
        
        df = pd.DataFrame(candles)
        
        analyzer = KeyLevelAnalyzer(false_break_lookback=lookback)
        result = analyzer.analyze(df)
        
        output = {
            "symbol": symbol,
            "interval": interval,
            "false_breaks": [fb.to_dict() for fb in result.false_breaks],
            "has_false_break": len(result.false_breaks) > 0,
            "current_price": float(df['close'].iloc[-1]),
        }
        
        # Add signal interpretation
        if result.false_breaks:
            latest = result.false_breaks[-1]
            if latest.type == "false_breakdown":
                output["signal"] = "BULLISH - Bear trap detected, potential reversal up"
            else:
                output["signal"] = "BEARISH - Bull trap detected, potential reversal down"
        else:
            output["signal"] = "No false break detected"
        
        return json.dumps(output, indent=2)
    
    except Exception as e:
        logger.error(f"Error detecting false breaks: {e}")
        return json.dumps({"error": str(e)})
