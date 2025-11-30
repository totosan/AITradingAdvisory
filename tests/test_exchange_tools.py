"""
Tests for exchange_tools.py

Tests the exchange tool functions that wrap ExchangeManager for agent use.
"""
import pytest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_ticker():
    """Create a mock TickerData object."""
    from exchange_providers.base import TickerData
    return TickerData(
        symbol="BTCUSDT",
        last_price=95000.0,
        bid_price=94990.0,
        ask_price=95010.0,
        high_24h=96000.0,
        low_24h=93000.0,
        volume_24h=1000.0,
        volume_24h_usd=95000000.0,
        change_24h=2.5,
        timestamp=datetime.now(),
        provider="Bitget",
    )


@pytest.fixture
def mock_orderbook():
    """Create a mock OrderBookData object."""
    from exchange_providers.base import OrderBookData, OrderBookEntry
    return OrderBookData(
        symbol="BTCUSDT",
        bids=[
            OrderBookEntry(price=94990.0, size=1.5),
            OrderBookEntry(price=94980.0, size=2.3),
            OrderBookEntry(price=94970.0, size=3.1),
        ],
        asks=[
            OrderBookEntry(price=95010.0, size=0.8),
            OrderBookEntry(price=95020.0, size=1.2),
            OrderBookEntry(price=95030.0, size=2.0),
        ],
        timestamp=datetime.now(),
        provider="Bitget",
    )


@pytest.fixture
def mock_ohlcv():
    """Create mock CandleData list."""
    from exchange_providers.base import CandleData
    now = datetime.now()
    return [
        CandleData(
            timestamp=now,
            open=94000.0,
            high=95500.0,
            low=93500.0,
            close=95000.0,
            volume=100.0,
        ),
        CandleData(
            timestamp=now,
            open=95000.0,
            high=96000.0,
            low=94500.0,
            close=95500.0,
            volume=120.0,
        ),
    ]


@pytest.fixture(autouse=True)
def reset_manager():
    """Reset the exchange manager before each test."""
    from exchange_tools import reset_exchange_manager
    reset_exchange_manager()
    yield
    reset_exchange_manager()


# ============================================================================
# get_realtime_price Tests
# ============================================================================

class TestGetRealtimePrice:
    """Tests for get_realtime_price function."""
    
    @patch('exchange_tools.get_exchange_manager')
    def test_get_realtime_price_success(self, mock_get_manager, mock_ticker):
        """Test successful price fetch."""
        from exchange_tools import get_realtime_price
        
        mock_manager = MagicMock()
        mock_manager.get_ticker.return_value = mock_ticker
        mock_get_manager.return_value = mock_manager
        
        result = get_realtime_price("BTCUSDT")
        data = json.loads(result)
        
        assert data["symbol"] == "BTCUSDT"
        assert data["price"] == 95000.0
        assert data["bid_price"] == 94990.0
        assert data["ask_price"] == 95010.0
        assert data["spread"] == 20.0
        assert data["provider"] == "Bitget"
    
    @patch('exchange_tools.get_exchange_manager')
    def test_get_realtime_price_with_provider(self, mock_get_manager, mock_ticker):
        """Test price fetch with specific provider."""
        from exchange_tools import get_realtime_price
        from exchange_providers import ProviderType
        
        mock_manager = MagicMock()
        mock_manager.get_ticker.return_value = mock_ticker
        mock_get_manager.return_value = mock_manager
        
        result = get_realtime_price("BTCUSDT", provider="bitget")
        
        # Verify provider was passed correctly
        mock_manager.get_ticker.assert_called_once()
        call_args = mock_manager.get_ticker.call_args
        assert call_args[0][0] == "BTCUSDT"
        assert call_args[1]["provider"] == ProviderType.BITGET
    
    @patch('exchange_tools.get_exchange_manager')
    def test_get_realtime_price_error(self, mock_get_manager):
        """Test error handling in price fetch."""
        from exchange_tools import get_realtime_price
        
        mock_manager = MagicMock()
        mock_manager.get_ticker.side_effect = Exception("API error")
        mock_get_manager.return_value = mock_manager
        
        result = get_realtime_price("BTCUSDT")
        data = json.loads(result)
        
        assert "error" in data
        assert "API error" in data["error"]


# ============================================================================
# get_price_comparison Tests
# ============================================================================

class TestGetPriceComparison:
    """Tests for get_price_comparison function."""
    
    @patch('exchange_tools.get_exchange_manager')
    def test_compare_prices_success(self, mock_get_manager):
        """Test successful price comparison."""
        from exchange_tools import get_price_comparison
        
        mock_manager = MagicMock()
        mock_manager.compare_prices.return_value = {
            "prices": {"Bitget": 95000.0, "CoinGecko": 94980.0},
            "average": 94990.0,
            "spread_pct": 0.021,
        }
        mock_get_manager.return_value = mock_manager
        
        result = get_price_comparison("BTCUSDT")
        data = json.loads(result)
        
        assert "prices" in data
        assert len(data["prices"]) == 2
        assert data["average"] == 94990.0
    
    @patch('exchange_tools.get_exchange_manager')
    def test_compare_prices_error(self, mock_get_manager):
        """Test error handling in price comparison."""
        from exchange_tools import get_price_comparison
        
        mock_manager = MagicMock()
        mock_manager.compare_prices.side_effect = Exception("Network error")
        mock_get_manager.return_value = mock_manager
        
        result = get_price_comparison("BTCUSDT")
        data = json.loads(result)
        
        assert "error" in data


# ============================================================================
# get_orderbook_depth Tests
# ============================================================================

class TestGetOrderbookDepth:
    """Tests for get_orderbook_depth function."""
    
    @patch('exchange_tools.get_exchange_manager')
    def test_get_orderbook_success(self, mock_get_manager, mock_orderbook):
        """Test successful orderbook fetch."""
        from exchange_tools import get_orderbook_depth
        
        mock_manager = MagicMock()
        mock_manager.get_orderbook.return_value = mock_orderbook
        mock_get_manager.return_value = mock_manager
        
        result = get_orderbook_depth("BTCUSDT", limit=3)
        data = json.loads(result)
        
        assert data["symbol"] == "BTCUSDT"
        assert len(data["bids"]) == 3
        assert len(data["asks"]) == 3
        assert data["bids"][0][0] == 94990.0  # First bid price
        assert data["spread"] == 20.0  # 95010 - 94990
    
    @patch('exchange_tools.get_exchange_manager')
    def test_get_orderbook_error(self, mock_get_manager):
        """Test error handling in orderbook fetch."""
        from exchange_tools import get_orderbook_depth
        
        mock_manager = MagicMock()
        mock_manager.get_orderbook.side_effect = Exception("Bitget unavailable")
        mock_get_manager.return_value = mock_manager
        
        result = get_orderbook_depth("BTCUSDT")
        data = json.loads(result)
        
        assert "error" in data


# ============================================================================
# get_ohlcv_data Tests
# ============================================================================

class TestGetOHLCVData:
    """Tests for get_ohlcv_data function."""
    
    @patch('exchange_tools.get_exchange_manager')
    def test_get_ohlcv_success(self, mock_get_manager, mock_ohlcv):
        """Test successful OHLCV data fetch."""
        from exchange_tools import get_ohlcv_data
        
        mock_manager = MagicMock()
        mock_manager.get_candles.return_value = mock_ohlcv
        mock_get_manager.return_value = mock_manager
        
        result = get_ohlcv_data("BTCUSDT", interval="1h", limit=2)
        data = json.loads(result)
        
        assert data["symbol"] == "BTCUSDT"
        assert data["interval"] == "1h"
        assert len(data["candles"]) == 2
        assert data["candles"][0]["close"] == 95000.0
    
    @patch('exchange_tools.get_exchange_manager')
    def test_get_ohlcv_empty(self, mock_get_manager):
        """Test OHLCV with no data."""
        from exchange_tools import get_ohlcv_data
        
        mock_manager = MagicMock()
        mock_manager.get_candles.return_value = []
        mock_get_manager.return_value = mock_manager
        
        result = get_ohlcv_data("BTCUSDT")
        data = json.loads(result)
        
        assert data["candles"] == []
        assert data["count"] == 0


# ============================================================================
# ExchangeManager Initialization Tests
# ============================================================================

class TestExchangeManagerInit:
    """Tests for exchange manager initialization."""
    
    @patch('exchange_tools.CoinGeckoProvider')
    def test_manager_initializes_coingecko(self, mock_coingecko_class):
        """Test that CoinGecko provider is always registered."""
        from exchange_tools import get_exchange_manager, reset_exchange_manager
        
        reset_exchange_manager()
        mock_coingecko_class.return_value = MagicMock()
        
        manager = get_exchange_manager()
        
        # CoinGecko should be registered
        mock_coingecko_class.assert_called_once()
    
    def test_reset_manager(self):
        """Test that reset_exchange_manager clears the global instance."""
        from exchange_tools import get_exchange_manager, reset_exchange_manager
        
        manager1 = get_exchange_manager()
        reset_exchange_manager()
        manager2 = get_exchange_manager()
        
        # Should be different instances after reset
        assert manager1 is not manager2


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Edge case tests for exchange tools."""
    
    @patch('exchange_tools.get_exchange_manager')
    def test_null_bid_ask_spread(self, mock_get_manager):
        """Test handling of missing bid/ask prices."""
        from exchange_tools import get_realtime_price
        from exchange_providers.base import TickerData
        
        # Ticker without bid/ask (e.g., from CoinGecko)
        ticker = TickerData(
            symbol="bitcoin",
            last_price=95000.0,
            bid_price=None,
            ask_price=None,
            high_24h=96000.0,
            low_24h=93000.0,
            volume_24h=None,
            volume_24h_usd=95000000.0,
            change_24h=2.5,
            timestamp=datetime.now(),
            provider="CoinGecko",
        )
        
        mock_manager = MagicMock()
        mock_manager.get_ticker.return_value = ticker
        mock_get_manager.return_value = mock_manager
        
        result = get_realtime_price("bitcoin")
        data = json.loads(result)
        
        assert data["spread"] is None
        assert data["bid_price"] is None
        assert data["ask_price"] is None
    
    @patch('exchange_tools.get_exchange_manager')
    def test_provider_case_insensitive(self, mock_get_manager, mock_ticker):
        """Test that provider parameter is case-insensitive."""
        from exchange_tools import get_realtime_price
        from exchange_providers import ProviderType
        
        mock_manager = MagicMock()
        mock_manager.get_ticker.return_value = mock_ticker
        mock_get_manager.return_value = mock_manager
        
        # Test different cases
        for provider_str in ["BITGET", "Bitget", "bitget", "COINGECKO", "CoinGecko"]:
            get_realtime_price("BTCUSDT", provider=provider_str)
        
        assert mock_manager.get_ticker.call_count == 5
