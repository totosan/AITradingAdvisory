"""
Tests for Stock Market Tools and Intent Router Asset Type Detection

Tests:
- Yahoo Finance provider functionality
- Stock price fetching
- Intent router asset type detection (crypto vs stock)
- Provider routing based on asset type
"""

import pytest
import json
from unittest.mock import patch, MagicMock

# Test Intent Router Asset Type Detection
class TestIntentRouterAssetType:
    """Tests for asset type detection in the Intent Router."""
    
    def test_detects_crypto_symbols(self):
        """Test detection of cryptocurrency symbols."""
        from intent_router import IntentRouter, AssetType
        
        router = IntentRouter(use_llm=False)
        
        # Test crypto symbols
        symbols, asset_type = router._extract_symbols("What is the price of BTC?")
        assert asset_type == AssetType.CRYPTO
        assert any("BTC" in s for s in symbols)
        
        symbols, asset_type = router._extract_symbols("Analyze ETH and SOL")
        assert asset_type == AssetType.CRYPTO
        assert len(symbols) >= 2
    
    def test_detects_stock_symbols(self):
        """Test detection of stock symbols."""
        from intent_router import IntentRouter, AssetType
        
        router = IntentRouter(use_llm=False)
        
        # Test stock symbols
        symbols, asset_type = router._extract_symbols("What is the price of AAPL?")
        assert asset_type == AssetType.STOCK
        assert "AAPL" in symbols
        
        symbols, asset_type = router._extract_symbols("Analyze MSFT and NVDA")
        assert asset_type == AssetType.STOCK
        assert len(symbols) >= 2
    
    def test_detects_german_stocks(self):
        """Test detection of German stock symbols."""
        from intent_router import IntentRouter, AssetType
        
        router = IntentRouter(use_llm=False)
        
        # Test German stocks with exchange suffix
        symbols, asset_type = router._extract_symbols("Show me SAP.DE price")
        assert asset_type == AssetType.STOCK
        assert "SAP.DE" in symbols
        
        # Test German stock by name
        symbols, asset_type = router._extract_symbols("Analyze Siemens stock")
        assert asset_type == AssetType.STOCK
    
    def test_detects_indices(self):
        """Test detection of market indices."""
        from intent_router import IntentRouter, AssetType
        
        router = IntentRouter(use_llm=False)
        
        symbols, asset_type = router._extract_symbols("What is ^GSPC doing?")
        assert asset_type == AssetType.STOCK
        assert "^GSPC" in symbols
    
    def test_keywords_affect_detection(self):
        """Test that keywords affect asset type detection."""
        from intent_router import IntentRouter, AssetType
        
        router = IntentRouter(use_llm=False)
        
        # Stock keyword should trigger stock detection
        symbols, asset_type = router._extract_symbols("Show me a stock analysis")
        assert asset_type == AssetType.STOCK
        
        # Crypto keyword should trigger crypto detection
        symbols, asset_type = router._extract_symbols("What crypto should I buy?")
        assert asset_type == AssetType.CRYPTO
    
    def test_pattern_classification_includes_asset_type(self):
        """Test that pattern classification includes asset type."""
        from intent_router import IntentRouter, AssetType, IntentType
        
        router = IntentRouter(use_llm=False)
        
        # Crypto intent
        intent = router.classify("BTC price")
        assert intent.type == IntentType.SIMPLE_LOOKUP
        assert intent.asset_type == AssetType.CRYPTO
        assert intent.tool_hint == "get_realtime_price"
        
        # Stock intent
        intent = router.classify("AAPL price")
        assert intent.type == IntentType.SIMPLE_LOOKUP
        assert intent.asset_type == AssetType.STOCK
        assert intent.tool_hint == "get_stock_price"


class TestYahooFinanceProvider:
    """Tests for Yahoo Finance provider."""
    
    def test_provider_type(self):
        """Test provider type is correct."""
        from exchange_providers import YahooFinanceProvider, ProviderType
        
        provider = YahooFinanceProvider()
        assert provider.provider_type == ProviderType.YAHOO_FINANCE
        assert provider.name == "Yahoo Finance"
        assert provider.requires_auth == False
    
    def test_normalize_symbol(self):
        """Test symbol normalization."""
        from exchange_providers import YahooFinanceProvider
        
        provider = YahooFinanceProvider()
        
        # Company names should be normalized
        assert provider.normalize_symbol("APPLE") == "AAPL"
        assert provider.normalize_symbol("Microsoft") == "MSFT"
        assert provider.normalize_symbol("GOOGLE") == "GOOGL"
        
        # Already correct symbols should pass through
        assert provider.normalize_symbol("AAPL") == "AAPL"
        assert provider.normalize_symbol("NVDA") == "NVDA"
    
    def test_is_stock_symbol(self):
        """Test stock symbol detection."""
        from exchange_providers import YahooFinanceProvider
        
        # Known stocks
        assert YahooFinanceProvider.is_stock_symbol("AAPL") == True
        assert YahooFinanceProvider.is_stock_symbol("MSFT") == True
        assert YahooFinanceProvider.is_stock_symbol("SPY") == True
        
        # German stocks with suffix
        assert YahooFinanceProvider.is_stock_symbol("SAP.DE") == True
        assert YahooFinanceProvider.is_stock_symbol("BMW.DE") == True
        
        # Indices
        assert YahooFinanceProvider.is_stock_symbol("^GSPC") == True
        assert YahooFinanceProvider.is_stock_symbol("^DJI") == True
        
        # Not stocks (crypto)
        assert YahooFinanceProvider.is_stock_symbol("BTC") == False
        assert YahooFinanceProvider.is_stock_symbol("ETH") == False


class TestAssetTypeEnum:
    """Tests for AssetType enum in base module."""
    
    def test_asset_type_values(self):
        """Test AssetType enum has expected values."""
        from exchange_providers import AssetType
        
        assert AssetType.CRYPTO.value == "crypto"
        assert AssetType.STOCK.value == "stock"
        assert AssetType.UNKNOWN.value == "unknown"


class TestExchangeManagerWithStocks:
    """Tests for ExchangeManager with stock support."""
    
    def test_manager_registers_yahoo_finance(self):
        """Test that manager can register Yahoo Finance provider."""
        from exchange_providers import (
            ExchangeManager, ProviderType, YahooFinanceProvider
        )
        
        manager = ExchangeManager()
        manager.register_provider(ProviderType.YAHOO_FINANCE, YahooFinanceProvider())
        
        assert ProviderType.YAHOO_FINANCE in manager.available_providers
    
    def test_detect_asset_type_function(self):
        """Test the detect_asset_type helper function."""
        from exchange_providers.manager import detect_asset_type, AssetType
        
        # Crypto
        assert detect_asset_type("BTCUSDT") == AssetType.CRYPTO
        assert detect_asset_type("bitcoin") == AssetType.CRYPTO
        assert detect_asset_type("ETH") == AssetType.CRYPTO
        
        # Stocks
        assert detect_asset_type("AAPL") == AssetType.STOCK
        assert detect_asset_type("^GSPC") == AssetType.STOCK
        assert detect_asset_type("SAP.DE") == AssetType.STOCK


class TestIntentHelperMethods:
    """Tests for Intent helper methods."""
    
    def test_is_crypto_method(self):
        """Test Intent.is_crypto() method."""
        from intent_router import Intent, IntentType, AssetType
        
        crypto_intent = Intent(
            type=IntentType.SIMPLE_LOOKUP,
            confidence=0.9,
            asset_type=AssetType.CRYPTO
        )
        assert crypto_intent.is_crypto() == True
        assert crypto_intent.is_stock() == False
    
    def test_is_stock_method(self):
        """Test Intent.is_stock() method."""
        from intent_router import Intent, IntentType, AssetType
        
        stock_intent = Intent(
            type=IntentType.SIMPLE_LOOKUP,
            confidence=0.9,
            asset_type=AssetType.STOCK
        )
        assert stock_intent.is_stock() == True
        assert stock_intent.is_crypto() == False


# Integration test (requires yfinance)
@pytest.mark.integration
class TestYahooFinanceIntegration:
    """Integration tests that actually call Yahoo Finance API."""
    
    def test_get_real_stock_ticker(self):
        """Test fetching real stock data from Yahoo Finance."""
        from exchange_providers import YahooFinanceProvider
        
        provider = YahooFinanceProvider()
        ticker = provider.get_ticker("AAPL")
        
        assert ticker.symbol == "AAPL"
        assert ticker.last_price > 0
        assert ticker.provider == "Yahoo Finance"
    
    def test_get_real_stock_candles(self):
        """Test fetching real candlestick data."""
        from exchange_providers import YahooFinanceProvider
        
        provider = YahooFinanceProvider()
        candles = provider.get_candles("AAPL", interval="1d", limit=5)
        
        assert len(candles) > 0
        assert candles[0].close > 0
