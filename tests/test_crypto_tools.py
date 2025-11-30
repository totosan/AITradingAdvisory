"""
Tests for crypto_tools.py

Tests the CryptoDataFetcher and TechnicalIndicators classes.
"""
import pytest
import json
from unittest.mock import MagicMock, patch

from crypto_tools import (
    CryptoDataFetcher,
    TechnicalIndicators,
    get_crypto_price,
    get_historical_data,
    get_market_info,
)
from cache import api_cache


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the API cache before each test."""
    api_cache.clear()
    yield
    api_cache.clear()


# ============================================================================
# CryptoDataFetcher Tests
# ============================================================================

class TestCryptoDataFetcher:
    """Tests for CryptoDataFetcher class."""
    
    def test_init_default(self):
        """Test default initialization without providers."""
        fetcher = CryptoDataFetcher(use_providers=False)
        assert fetcher.coingecko_base == "https://api.coingecko.com/api/v3"
        assert fetcher._use_providers is False
    
    @patch('crypto_tools.requests.get')
    def test_get_crypto_price_success(self, mock_get, mock_coingecko_price_response):
        """Test successful price fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_coingecko_price_response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        fetcher = CryptoDataFetcher()
        result = fetcher.get_crypto_price("bitcoin")
        
        # Verify API was called correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "bitcoin" in call_args[1]['params']['ids']
        
        # Verify response is valid JSON
        data = json.loads(result)
        assert "bitcoin" in data
        assert "usd" in data["bitcoin"]
        assert data["bitcoin"]["usd"] == 95000.00
    
    @patch('crypto_tools.requests.get')
    def test_get_crypto_price_not_found(self, mock_get):
        """Test price fetch for unknown cryptocurrency."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # Empty response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        fetcher = CryptoDataFetcher()
        result = fetcher.get_crypto_price("unknowncoin")
        
        assert "not found" in result.lower() or "error" in result.lower()
    
    @patch('crypto_tools.requests.get')
    def test_get_crypto_price_api_error(self, mock_get):
        """Test price fetch with API error."""
        mock_get.side_effect = Exception("Connection timeout")
        
        fetcher = CryptoDataFetcher()
        result = fetcher.get_crypto_price("bitcoin")
        
        assert "error" in result.lower()
        assert "Connection timeout" in result
    
    @patch('crypto_tools.requests.get')
    def test_get_historical_data_success(self, mock_get, mock_coingecko_historical_data):
        """Test successful historical data fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_coingecko_historical_data
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        fetcher = CryptoDataFetcher()
        result = fetcher.get_historical_data("bitcoin", days=30)
        
        # Verify response structure
        data = json.loads(result)
        assert "symbol" in data
        assert "days" in data
        assert "latest_price" in data
        assert "price_change_pct" in data
    
    @patch('crypto_tools.requests.get')
    def test_get_historical_data_limits_days(self, mock_get, mock_coingecko_historical_data):
        """Test that days are limited to 365."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_coingecko_historical_data
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        fetcher = CryptoDataFetcher()
        fetcher.get_historical_data("bitcoin", days=1000)
        
        # Verify the API was called with max 365 days
        call_args = mock_get.call_args
        assert call_args[1]['params']['days'] <= 365
    
    @patch('crypto_tools.requests.get')
    def test_get_market_info_success(self, mock_get, mock_coingecko_market_data):
        """Test successful market info fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_coingecko_market_data
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        fetcher = CryptoDataFetcher()
        result = fetcher.get_market_info("bitcoin")
        
        data = json.loads(result)
        assert "name" in data
        assert "current_price_usd" in data
        assert "market_cap_usd" in data


# ============================================================================
# TechnicalIndicators Tests
# ============================================================================

class TestTechnicalIndicators:
    """Tests for TechnicalIndicators class."""
    
    def test_calculate_sma_basic(self):
        """Test basic SMA calculation."""
        prices = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        sma = TechnicalIndicators.calculate_sma(prices, period=5)
        
        assert len(sma) == 7  # 11 - 5 + 1
        assert sma[0] == 12.0  # (10+11+12+13+14)/5
        assert sma[-1] == 18.0  # (16+17+18+19+20)/5
    
    def test_calculate_sma_insufficient_data(self):
        """Test SMA with insufficient data."""
        prices = [10, 11, 12]
        sma = TechnicalIndicators.calculate_sma(prices, period=5)
        
        assert sma == []
    
    def test_calculate_ema_basic(self):
        """Test basic EMA calculation."""
        prices = [22, 22.27, 22.19, 22.08, 22.17, 22.18, 22.13, 22.23, 22.43, 22.24, 22.29]
        ema = TechnicalIndicators.calculate_ema(prices, period=5)
        
        assert len(ema) > 0
        # First EMA should be the SMA of first 5 prices
        expected_first = sum(prices[:5]) / 5
        assert abs(ema[0] - expected_first) < 0.01
    
    def test_calculate_ema_insufficient_data(self):
        """Test EMA with insufficient data."""
        prices = [10, 11, 12]
        ema = TechnicalIndicators.calculate_ema(prices, period=5)
        
        assert ema == []
    
    def test_calculate_rsi_basic(self):
        """Test basic RSI calculation."""
        # Create trending data for predictable RSI
        prices = [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84,
                  46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03]
        rsi = TechnicalIndicators.calculate_rsi(prices, period=14)
        
        assert len(rsi) > 0
        # RSI should be between 0 and 100
        for value in rsi:
            assert 0 <= value <= 100
    
    def test_calculate_rsi_insufficient_data(self):
        """Test RSI with insufficient data."""
        prices = [10, 11, 12, 13, 14]
        rsi = TechnicalIndicators.calculate_rsi(prices, period=14)
        
        assert rsi == []
    
    def test_calculate_rsi_all_gains(self):
        """Test RSI with all gains (should approach 100)."""
        prices = [i for i in range(1, 20)]  # Strictly increasing
        rsi = TechnicalIndicators.calculate_rsi(prices, period=14)
        
        if rsi:
            # With all gains, RSI should be 100
            assert rsi[-1] == 100
    
    def test_calculate_macd_basic(self):
        """Test basic MACD calculation."""
        # Generate enough price data for MACD (need at least 26 for slow EMA)
        prices = [100 + i * 0.5 + (i % 5) for i in range(50)]
        macd_line, signal_line, histogram = TechnicalIndicators.calculate_macd(prices)
        
        # Verify we got results
        assert len(macd_line) > 0, "MACD line should not be empty"
        assert len(signal_line) > 0, "Signal line should not be empty"
        assert len(histogram) > 0, "Histogram should not be empty"
        
        # Signal line should be shorter than MACD line (9-period EMA of MACD)
        assert len(signal_line) <= len(macd_line)
        
        # Histogram should match signal line length
        assert len(histogram) == len(signal_line)


# ============================================================================
# Module-level Function Tests
# ============================================================================

class TestModuleFunctions:
    """Test the module-level wrapper functions."""
    
    @patch('crypto_tools.requests.get')
    def test_get_crypto_price_function(self, mock_get, mock_coingecko_price_response):
        """Test the module-level get_crypto_price function."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_coingecko_price_response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        result = get_crypto_price("bitcoin")
        
        assert "bitcoin" in result.lower() or "95000" in result
    
    @patch('crypto_tools.requests.get')
    def test_get_historical_data_function(self, mock_get, mock_coingecko_historical_data):
        """Test the module-level get_historical_data function."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_coingecko_historical_data
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        result = get_historical_data("bitcoin", 30)
        
        assert "bitcoin" in result.lower() or "price" in result.lower()


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_sma_empty_list(self):
        """Test SMA with empty price list."""
        assert TechnicalIndicators.calculate_sma([], period=5) == []
    
    def test_ema_empty_list(self):
        """Test EMA with empty price list."""
        assert TechnicalIndicators.calculate_ema([], period=5) == []
    
    def test_rsi_empty_list(self):
        """Test RSI with empty price list."""
        assert TechnicalIndicators.calculate_rsi([], period=14) == []
    
    def test_sma_single_element(self):
        """Test SMA with single element."""
        assert TechnicalIndicators.calculate_sma([100], period=1) == [100]
    
    @patch('crypto_tools.requests.get')
    def test_network_timeout(self, mock_get):
        """Test handling of network timeout."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")
        
        fetcher = CryptoDataFetcher()
        result = fetcher.get_crypto_price("bitcoin")
        
        assert "error" in result.lower()
    
    @patch('crypto_tools.requests.get')
    def test_invalid_json_response(self, mock_get):
        """Test handling of invalid JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        fetcher = CryptoDataFetcher()
        result = fetcher.get_crypto_price("bitcoin")
        
        assert "error" in result.lower()
