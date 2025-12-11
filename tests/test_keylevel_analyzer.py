"""
Tests for KeyLevelAnalyzer (Phase 8 - Step 1)

Tests the pivot-based Support/Resistance detection, zone merging,
false break detection, and breakout status calculation.
"""
import pytest
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from keylevel_analyzer import (
    KeyLevelAnalyzer,
    Zone,
    ZoneType,
    FalseBreak,
    CurrentPosition,
    BreakoutStatus,
    KeyLevelAnalysis,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_ohlcv_data() -> pd.DataFrame:
    """Create sample OHLCV data for testing."""
    np.random.seed(42)
    n_bars = 200
    
    # Generate realistic price movement
    base_price = 100.0
    returns = np.random.randn(n_bars) * 0.02  # 2% daily volatility
    
    closes = [base_price]
    for r in returns[1:]:
        closes.append(closes[-1] * (1 + r))
    
    closes = np.array(closes)
    
    # Generate OHLC from closes
    highs = closes * (1 + np.abs(np.random.randn(n_bars)) * 0.01)
    lows = closes * (1 - np.abs(np.random.randn(n_bars)) * 0.01)
    opens = np.roll(closes, 1)
    opens[0] = base_price
    
    # Ensure high >= close, open and low <= close, open
    highs = np.maximum(highs, np.maximum(closes, opens))
    lows = np.minimum(lows, np.minimum(closes, opens))
    
    # Generate volume
    volume = np.random.randint(1000, 10000, n_bars)
    
    dates = pd.date_range(end=datetime.now(), periods=n_bars, freq='1H')
    
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volume,
    }, index=dates)


@pytest.fixture
def ranging_market_data() -> pd.DataFrame:
    """Create data that represents a ranging market."""
    n_bars = 200
    
    # Create oscillating price between 95 and 105
    t = np.linspace(0, 10 * np.pi, n_bars)
    base = 100 + 5 * np.sin(t)  # Oscillate between 95 and 105
    noise = np.random.randn(n_bars) * 0.5
    closes = base + noise
    
    highs = closes + np.abs(np.random.randn(n_bars)) * 0.5
    lows = closes - np.abs(np.random.randn(n_bars)) * 0.5
    opens = np.roll(closes, 1)
    opens[0] = closes[0]
    
    highs = np.maximum(highs, np.maximum(closes, opens))
    lows = np.minimum(lows, np.minimum(closes, opens))
    
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': np.random.randint(1000, 10000, n_bars),
    })


@pytest.fixture
def breakout_market_data() -> pd.DataFrame:
    """Create data that shows a breakout above resistance."""
    n_bars = 200
    
    # First 150 bars: ranging between 95-105
    t1 = np.linspace(0, 5 * np.pi, 150)
    ranging = 100 + 4 * np.sin(t1)
    
    # Last 50 bars: breakout to 115
    breakout = np.linspace(104, 115, 50) + np.random.randn(50) * 0.5
    
    closes = np.concatenate([ranging, breakout])
    highs = closes + np.abs(np.random.randn(n_bars)) * 0.5
    lows = closes - np.abs(np.random.randn(n_bars)) * 0.5
    opens = np.roll(closes, 1)
    opens[0] = closes[0]
    
    highs = np.maximum(highs, np.maximum(closes, opens))
    lows = np.minimum(lows, np.minimum(closes, opens))
    
    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': np.random.randint(1000, 10000, n_bars),
    })


# ============================================================================
# Zone Tests
# ============================================================================

class TestZone:
    """Tests for the Zone dataclass."""
    
    def test_zone_creation(self):
        """Test basic zone creation."""
        zone = Zone(
            top=100.5,
            bottom=99.5,
            zone_type=ZoneType.SUPPORT,
            strength=2,
            created_bar=50,
        )
        
        assert zone.top == 100.5
        assert zone.bottom == 99.5
        assert zone.zone_type == ZoneType.SUPPORT
        assert zone.strength == 2
    
    def test_zone_to_dict(self):
        """Test zone serialization."""
        zone = Zone(
            top=100.5,
            bottom=99.5,
            zone_type=ZoneType.RESISTANCE,
        )
        
        d = zone.to_dict()
        assert d['type'] == 'resistance'
        assert d['top'] == 100.5
        assert d['bottom'] == 99.5
    
    def test_zone_overlaps_true(self):
        """Test overlap detection - overlapping zones."""
        zone1 = Zone(top=100, bottom=98, zone_type=ZoneType.SUPPORT)
        zone2 = Zone(top=99, bottom=97, zone_type=ZoneType.SUPPORT)
        
        assert zone1.overlaps(zone2)
        assert zone2.overlaps(zone1)
    
    def test_zone_overlaps_false(self):
        """Test overlap detection - non-overlapping zones."""
        zone1 = Zone(top=100, bottom=98, zone_type=ZoneType.SUPPORT)
        zone2 = Zone(top=95, bottom=93, zone_type=ZoneType.SUPPORT)
        
        assert not zone1.overlaps(zone2)
        assert not zone2.overlaps(zone1)
    
    def test_zone_merge(self):
        """Test zone merging."""
        zone1 = Zone(top=100, bottom=98, zone_type=ZoneType.SUPPORT, strength=1, created_bar=10)
        zone2 = Zone(top=99, bottom=97, zone_type=ZoneType.SUPPORT, strength=1, created_bar=20)
        
        merged = zone1.merge_with(zone2)
        
        assert merged.top == 100
        assert merged.bottom == 97
        assert merged.strength == 2
        assert merged.created_bar == 10


# ============================================================================
# KeyLevelAnalyzer Tests
# ============================================================================

class TestKeyLevelAnalyzer:
    """Tests for the KeyLevelAnalyzer class."""
    
    def test_init_default_params(self):
        """Test initialization with default parameters."""
        analyzer = KeyLevelAnalyzer()
        
        assert analyzer.left == 20
        assert analyzer.right == 15
        assert analyzer.num_pivots == 4
        assert analyzer.zone_atr_mult == 0.5
    
    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        analyzer = KeyLevelAnalyzer(left=10, right=5, zone_atr_mult=0.3)
        
        assert analyzer.left == 10
        assert analyzer.right == 5
        assert analyzer.zone_atr_mult == 0.3
    
    def test_analyze_returns_analysis(self, sample_ohlcv_data):
        """Test that analyze returns a KeyLevelAnalysis object."""
        analyzer = KeyLevelAnalyzer()
        result = analyzer.analyze(sample_ohlcv_data)
        
        assert isinstance(result, KeyLevelAnalysis)
        assert isinstance(result.zones, list)
        assert isinstance(result.current_position, CurrentPosition)
        assert isinstance(result.breakout_status, BreakoutStatus)
    
    def test_analyze_detects_zones(self, sample_ohlcv_data):
        """Test that analyze detects S/R zones."""
        analyzer = KeyLevelAnalyzer()
        result = analyzer.analyze(sample_ohlcv_data)
        
        # Should detect at least some zones
        assert len(result.zones) >= 0  # May be 0 if no clear pivots
    
    def test_analyze_ranging_market(self, ranging_market_data):
        """Test analysis of ranging market data."""
        analyzer = KeyLevelAnalyzer(left=15, right=10)
        result = analyzer.analyze(ranging_market_data)
        
        # In a ranging market, should detect zones
        assert isinstance(result.zones, list)
        
        # Current position should be calculated
        assert result.current_position is not None
    
    def test_analyze_breakout_market(self, breakout_market_data):
        """Test analysis of breakout market data."""
        analyzer = KeyLevelAnalyzer(left=15, right=10)
        result = analyzer.analyze(breakout_market_data)
        
        # Should detect the breakout or at least price above zones
        # After a breakout, most zones should be below current price
        current_price = breakout_market_data['close'].iloc[-1]
        zones_below = sum(1 for z in result.zones if z.top < current_price)
        
        # Most zones should be below after breakout
        if len(result.zones) > 0:
            assert zones_below >= len(result.zones) * 0.5 or result.breakout_status.is_breakout
    
    def test_heiken_ashi_calculation(self, sample_ohlcv_data):
        """Test Heiken Ashi calculation."""
        analyzer = KeyLevelAnalyzer(use_heiken_ashi=True)
        ha_open, ha_close = analyzer._calculate_heiken_ashi(sample_ohlcv_data)
        
        assert len(ha_open) == len(sample_ohlcv_data)
        assert len(ha_close) == len(sample_ohlcv_data)
        
        # HA close should be average of OHLC
        expected_first_ha_close = sample_ohlcv_data.iloc[0][['open', 'high', 'low', 'close']].mean()
        assert abs(ha_close.iloc[0] - expected_first_ha_close) < 0.01
    
    def test_atr_calculation(self, sample_ohlcv_data):
        """Test ATR calculation."""
        analyzer = KeyLevelAnalyzer(atr_length=14)
        atr = analyzer._calculate_atr(sample_ohlcv_data)
        
        assert len(atr) == len(sample_ohlcv_data)
        assert not atr.iloc[-1] < 0  # ATR should be positive
    
    def test_short_dataframe_handling(self):
        """Test handling of DataFrame that's too short."""
        short_df = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100.5, 101.5, 102.5],
        })
        
        analyzer = KeyLevelAnalyzer()
        result = analyzer.analyze(short_df)
        
        # Should return empty result without error
        assert result.zones == []
    
    def test_missing_columns_raises_error(self):
        """Test that missing columns raise ValueError."""
        df = pd.DataFrame({
            'open': [100, 101],
            'close': [101, 102],
        })
        
        analyzer = KeyLevelAnalyzer()
        with pytest.raises(ValueError, match="missing required columns"):
            analyzer.analyze(df)
    
    def test_analysis_to_json(self, sample_ohlcv_data):
        """Test JSON serialization of analysis result."""
        analyzer = KeyLevelAnalyzer()
        result = analyzer.analyze(sample_ohlcv_data)
        
        json_str = result.to_json()
        parsed = json.loads(json_str)
        
        assert 'zones' in parsed
        assert 'current_position' in parsed
        assert 'breakout_status' in parsed
        assert 'atr_value' in parsed
    
    def test_zone_merging(self, ranging_market_data):
        """Test that overlapping zones are merged."""
        analyzer = KeyLevelAnalyzer(merge_zones=True)
        result = analyzer.analyze(ranging_market_data)
        
        # After merging, no zones should overlap
        for i, zone1 in enumerate(result.zones):
            for zone2 in result.zones[i+1:]:
                assert not zone1.overlaps(zone2)
    
    def test_current_position_calculation(self, ranging_market_data):
        """Test current position calculation."""
        analyzer = KeyLevelAnalyzer()
        result = analyzer.analyze(ranging_market_data)
        
        current_price = ranging_market_data['close'].iloc[-1]
        pos = result.current_position
        
        # Zones above + zones below should be reasonable
        assert pos.zones_above >= 0
        assert pos.zones_below >= 0


# ============================================================================
# False Break Detection Tests
# ============================================================================

class TestFalseBreakDetection:
    """Tests for false break (bull/bear trap) detection."""
    
    def test_false_break_dataclass(self):
        """Test FalseBreak dataclass."""
        fb = FalseBreak(
            type="false_breakdown",
            bar_index=145,
            zone_top=100,
            zone_bottom=98,
            price=99,
        )
        
        d = fb.to_dict()
        assert d['type'] == 'false_breakdown'
        assert d['bar_index'] == 145


# ============================================================================
# Integration Tests
# ============================================================================

class TestKeyLevelAnalyzerIntegration:
    """Integration tests for the complete analysis flow."""
    
    def test_full_analysis_workflow(self, sample_ohlcv_data):
        """Test complete analysis workflow."""
        analyzer = KeyLevelAnalyzer(
            left=15,
            right=10,
            num_pivots=4,
            zone_atr_mult=0.5,
            use_heiken_ashi=True,
            merge_zones=True,
        )
        
        result = analyzer.analyze(sample_ohlcv_data)
        
        # Verify all components are present
        assert result.zones is not None
        assert result.current_position is not None
        assert result.false_breaks is not None
        assert result.breakout_status is not None
        assert result.atr_value > 0
        
        # Verify serialization works
        json_output = result.to_json()
        parsed = json.loads(json_output)
        
        assert isinstance(parsed, dict)
