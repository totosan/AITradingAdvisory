"""
Exchange Manager Module

This module provides a unified interface for managing multiple exchange
providers and aggregating data across platforms. It enables easy switching
between providers and comparison of prices across exchanges.

Usage:
    from exchange_providers import ExchangeManager, ProviderType
    from exchange_providers import CoinGeckoProvider, BitgetProvider
    
    manager = ExchangeManager()
    manager.register_provider(ProviderType.COINGECKO, CoinGeckoProvider())
    manager.register_provider(ProviderType.BITGET, BitgetProvider.from_env())
    
    # Get ticker from specific provider
    ticker = manager.get_ticker("BTCUSDT", provider=ProviderType.BITGET)
    
    # Get ticker from default provider
    ticker = manager.get_ticker("BTCUSDT")
    
    # Compare prices across providers
    comparison = manager.compare_prices("BTCUSDT")
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Union

from .base import (
    ExchangeProvider,
    ProviderType,
    TickerData,
    CandleData,
    OrderBookData,
    TradeData,
    AccountBalance,
)


class ExchangeManager:
    """
    Manages multiple exchange providers and provides unified access.
    
    Features:
    - Register and manage multiple exchange providers
    - Set default provider for operations
    - Get data from specific provider or aggregate from all
    - Compare prices across exchanges
    - Automatic fallback to alternative providers on failure
    
    Usage:
        manager = ExchangeManager()
        manager.register_provider(ProviderType.BITGET, BitgetProvider.from_env())
        manager.set_default_provider(ProviderType.BITGET)
        
        # All subsequent calls use Bitget unless specified otherwise
        ticker = manager.get_ticker("BTCUSDT")
    """
    
    def __init__(self, default_provider: Optional[ProviderType] = None):
        """
        Initialize the exchange manager.
        
        Args:
            default_provider: Initial default provider type
        """
        self._providers: Dict[ProviderType, ExchangeProvider] = {}
        self._default_provider: Optional[ProviderType] = default_provider
    
    # ==================== Provider Management ====================
    
    def register_provider(
        self,
        provider_type: ProviderType,
        provider: ExchangeProvider,
    ) -> None:
        """
        Register an exchange provider.
        
        Args:
            provider_type: Provider type identifier
            provider: Provider instance
        """
        self._providers[provider_type] = provider
        
        # Set as default if first provider registered
        if self._default_provider is None:
            self._default_provider = provider_type
    
    def unregister_provider(self, provider_type: ProviderType) -> None:
        """
        Remove a registered provider.
        
        Args:
            provider_type: Provider type to remove
        """
        if provider_type in self._providers:
            del self._providers[provider_type]
            
            # Update default if we removed it
            if self._default_provider == provider_type:
                self._default_provider = next(iter(self._providers), None)
    
    def get_provider(
        self,
        provider_type: Optional[ProviderType] = None,
    ) -> ExchangeProvider:
        """
        Get a specific provider instance.
        
        Args:
            provider_type: Provider type (uses default if None)
            
        Returns:
            ExchangeProvider instance
            
        Raises:
            ValueError: If provider not registered
        """
        pt = provider_type or self._default_provider
        
        if pt is None:
            raise ValueError("No provider specified and no default set")
        
        if pt not in self._providers:
            raise ValueError(
                f"Provider '{pt.value}' not registered. "
                f"Available: {[p.value for p in self._providers.keys()]}"
            )
        
        return self._providers[pt]
    
    def set_default_provider(self, provider_type: ProviderType) -> None:
        """
        Set the default provider for operations.
        
        Args:
            provider_type: Provider to use as default
            
        Raises:
            ValueError: If provider not registered
        """
        if provider_type not in self._providers:
            raise ValueError(f"Provider '{provider_type.value}' not registered")
        
        self._default_provider = provider_type
    
    @property
    def default_provider(self) -> Optional[ProviderType]:
        """Get the current default provider type."""
        return self._default_provider
    
    @property
    def available_providers(self) -> List[ProviderType]:
        """Get list of registered provider types."""
        return list(self._providers.keys())
    
    # ==================== Market Data Operations ====================
    
    def get_ticker(
        self,
        symbol: str,
        provider: Optional[ProviderType] = None,
    ) -> TickerData:
        """
        Get ticker data from a specific or default provider.
        
        Args:
            symbol: Trading pair or coin symbol
            provider: Specific provider to use (optional)
            
        Returns:
            TickerData from the specified provider
        """
        return self.get_provider(provider).get_ticker(symbol)
    
    def get_candles(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100,
        provider: Optional[ProviderType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[CandleData]:
        """
        Get candlestick data from a specific or default provider.
        
        Args:
            symbol: Trading pair or coin symbol
            interval: Candle interval
            limit: Maximum candles to return
            provider: Specific provider to use (optional)
            start_time: Start time for historical data
            end_time: End time for historical data
            
        Returns:
            List of CandleData objects
        """
        return self.get_provider(provider).get_candles(
            symbol, interval, limit, start_time, end_time
        )
    
    def get_orderbook(
        self,
        symbol: str,
        limit: int = 50,
        provider: Optional[ProviderType] = None,
    ) -> OrderBookData:
        """
        Get order book from a provider that supports it.
        
        Args:
            symbol: Trading pair
            limit: Number of levels
            provider: Specific provider to use (optional)
            
        Returns:
            OrderBookData with bids and asks
        """
        return self.get_provider(provider).get_orderbook(symbol, limit)
    
    def get_recent_trades(
        self,
        symbol: str,
        limit: int = 100,
        provider: Optional[ProviderType] = None,
    ) -> List[TradeData]:
        """
        Get recent trades from a provider that supports it.
        
        Args:
            symbol: Trading pair
            limit: Maximum trades to return
            provider: Specific provider to use (optional)
            
        Returns:
            List of TradeData objects
        """
        return self.get_provider(provider).get_recent_trades(symbol, limit)
    
    # ==================== Aggregation Operations ====================
    
    def get_ticker_all_providers(self, symbol: str) -> Dict[str, TickerData]:
        """
        Get ticker data from all registered providers.
        
        Args:
            symbol: Trading pair or coin symbol
            
        Returns:
            Dictionary mapping provider name to TickerData
        """
        results = {}
        
        for provider_type, provider in self._providers.items():
            try:
                ticker = provider.get_ticker(symbol)
                results[provider.name] = ticker
            except Exception as e:
                # Log error but continue with other providers
                results[provider.name] = {"error": str(e)}
        
        return results
    
    def compare_prices(self, symbol: str) -> Dict[str, Any]:
        """
        Compare prices for a symbol across all providers.
        
        Args:
            symbol: Trading pair or coin symbol
            
        Returns:
            Dictionary with price comparison data
        """
        tickers = self.get_ticker_all_providers(symbol)
        
        prices = {}
        for provider_name, ticker in tickers.items():
            if isinstance(ticker, TickerData):
                prices[provider_name] = {
                    "price": ticker.last_price,
                    "change_24h": ticker.change_24h,
                    "volume_24h_usd": ticker.volume_24h_usd,
                }
            else:
                prices[provider_name] = ticker  # Contains error
        
        # Calculate statistics if we have valid prices
        valid_prices = [
            p["price"] for p in prices.values()
            if isinstance(p, dict) and "price" in p and p["price"]
        ]
        
        stats = {}
        if valid_prices:
            avg_price = sum(valid_prices) / len(valid_prices)
            stats = {
                "average_price": avg_price,
                "min_price": min(valid_prices),
                "max_price": max(valid_prices),
                "spread": max(valid_prices) - min(valid_prices),
                "spread_pct": (max(valid_prices) - min(valid_prices)) / avg_price * 100,
            }
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "prices": prices,
            "statistics": stats,
        }
    
    # ==================== Account Operations ====================
    
    def get_account_balance(
        self,
        coin: Optional[str] = None,
        provider: Optional[ProviderType] = None,
    ) -> List[AccountBalance]:
        """
        Get account balance from an authenticated provider.
        
        Args:
            coin: Specific coin to query (optional)
            provider: Specific provider to use (optional)
            
        Returns:
            List of AccountBalance objects
        """
        return self.get_provider(provider).get_account_balance(coin)
    
    # ==================== Health Check ====================
    
    def health_check(self) -> Dict[str, bool]:
        """
        Check health of all registered providers.
        
        Returns:
            Dictionary mapping provider name to health status
        """
        results = {}
        
        for provider_type, provider in self._providers.items():
            try:
                results[provider.name] = provider.health_check()
            except Exception:
                results[provider.name] = False
        
        return results
    
    def to_json_summary(self) -> str:
        """
        Get a JSON summary of the manager state.
        
        Returns:
            JSON string with manager configuration
        """
        return json.dumps({
            "default_provider": self._default_provider.value if self._default_provider else None,
            "available_providers": [p.value for p in self._providers.keys()],
            "provider_features": {
                provider.name: {
                    "requires_auth": provider.requires_auth,
                    "supports_futures": provider.supports_futures,
                    "supports_trading": provider.supports_trading,
                }
                for provider in self._providers.values()
            },
        }, indent=2)


# Factory function for easy setup
def create_exchange_manager(
    include_coingecko: bool = True,
    include_bitget: bool = True,
    default_provider: Optional[ProviderType] = None,
) -> ExchangeManager:
    """
    Create a pre-configured ExchangeManager.
    
    Args:
        include_coingecko: Register CoinGecko provider
        include_bitget: Register Bitget provider (from env vars)
        default_provider: Set as default provider
        
    Returns:
        Configured ExchangeManager instance
    """
    from .coingecko_provider import CoinGeckoProvider
    from .bitget_provider import BitgetProvider
    
    manager = ExchangeManager()
    
    if include_coingecko:
        manager.register_provider(ProviderType.COINGECKO, CoinGeckoProvider())
    
    if include_bitget:
        manager.register_provider(ProviderType.BITGET, BitgetProvider.from_env())
    
    if default_provider:
        manager.set_default_provider(default_provider)
    
    return manager
