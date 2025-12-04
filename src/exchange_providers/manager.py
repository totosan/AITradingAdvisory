"""
Exchange Manager Module

This module provides a unified interface for managing multiple exchange
providers and aggregating data across platforms. It enables easy switching
between providers and comparison of prices across exchanges.

**Default Behavior:**
- Bitget is the PRIMARY provider for real-time data
- CoinGecko is the FALLBACK provider (used when Bitget fails or for unsupported coins)
- Explicit provider selection always takes precedence

Usage:
    from exchange_providers import ExchangeManager, ProviderType
    from exchange_providers import CoinGeckoProvider, BitgetProvider
    
    manager = ExchangeManager()
    manager.register_provider(ProviderType.BITGET, BitgetProvider.from_env())
    manager.register_provider(ProviderType.COINGECKO, CoinGeckoProvider())
    
    # Get ticker from default provider (Bitget, with fallback to CoinGecko)
    ticker = manager.get_ticker("BTCUSDT")
    
    # Get ticker from specific provider (no fallback)
    ticker = manager.get_ticker("bitcoin", provider=ProviderType.COINGECKO)
    
    # Compare prices across providers
    comparison = manager.compare_prices("BTCUSDT")
"""

import json
import os
import logging
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

logger = logging.getLogger(__name__)


# Symbol mapping: CoinGecko IDs → Bitget trading pairs
COINGECKO_TO_BITGET_MAP = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "solana": "SOLUSDT",
    "sui": "SUIUSDT",
    "ripple": "XRPUSDT",
    "cardano": "ADAUSDT",
    "dogecoin": "DOGEUSDT",
    "polkadot": "DOTUSDT",
    "avalanche-2": "AVAXUSDT",
    "chainlink": "LINKUSDT",
    "polygon": "MATICUSDT",
    "litecoin": "LTCUSDT",
    "uniswap": "UNIUSDT",
    "cosmos": "ATOMUSDT",
    "stellar": "XLMUSDT",
    "near": "NEARUSDT",
    "aptos": "APTUSDT",
    "arbitrum": "ARBUSDT",
    "optimism": "OPUSDT",
    "injective-protocol": "INJUSDT",
    "render-token": "RNDR USDT",
    "filecoin": "FILUSDT",
    "hedera-hashgraph": "HBARUSDT",
    "tron": "TRXUSDT",
    "the-graph": "GRTUSDT",
    "aave": "AAVEUSDT",
    "maker": "MKRUSDT",
    "pepe": "PEPEUSDT",
    "shiba-inu": "SHIBUSDT",
    "bonk": "BONKUSDT",
}

# Reverse mapping: Bitget pairs → CoinGecko IDs
BITGET_TO_COINGECKO_MAP = {v: k for k, v in COINGECKO_TO_BITGET_MAP.items()}


class ExchangeManager:
    """
    Manages multiple exchange providers and provides unified access.
    
    Features:
    - Register and manage multiple exchange providers
    - Bitget as default provider with automatic fallback to CoinGecko
    - Get data from specific provider or use smart fallback
    - Compare prices across exchanges
    - Automatic symbol normalization between providers
    
    **Default Behavior:**
    - Bitget is the PRIMARY provider (best for real-time trading data)
    - CoinGecko is the FALLBACK provider (broader coin coverage)
    - When user explicitly requests a provider, no fallback is used
    
    Usage:
        manager = ExchangeManager()
        manager.register_provider(ProviderType.BITGET, BitgetProvider.from_env())
        manager.register_provider(ProviderType.COINGECKO, CoinGeckoProvider())
        
        # Uses Bitget by default, falls back to CoinGecko on failure
        ticker = manager.get_ticker("BTCUSDT")
        
        # Explicit provider selection (no fallback)
        ticker = manager.get_ticker("bitcoin", provider=ProviderType.COINGECKO)
    """
    
    def __init__(
        self,
        default_provider: Optional[ProviderType] = None,
        fallback_enabled: bool = True,
        fallback_provider: Optional[ProviderType] = None,
    ):
        """
        Initialize the exchange manager.
        
        Args:
            default_provider: Initial default provider type (defaults to BITGET)
            fallback_enabled: Whether to enable automatic fallback
            fallback_provider: Provider to use as fallback (defaults to COINGECKO)
        """
        self._providers: Dict[ProviderType, ExchangeProvider] = {}
        
        # Load from environment or use provided values
        env_default = os.getenv("EXCHANGE_DEFAULT_PROVIDER", "bitget").lower()
        env_fallback_enabled = os.getenv("EXCHANGE_FALLBACK_ENABLED", "true").lower() == "true"
        
        # Set default provider preference (Bitget first!)
        if default_provider is not None:
            self._default_provider = default_provider
        elif env_default == "bitget":
            self._default_provider = ProviderType.BITGET
        elif env_default == "coingecko":
            self._default_provider = ProviderType.COINGECKO
        else:
            self._default_provider = ProviderType.BITGET  # Bitget as ultimate default
        
        # Fallback configuration
        self._fallback_enabled = fallback_enabled and env_fallback_enabled
        self._fallback_provider = fallback_provider or ProviderType.COINGECKO
    
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
    
    @property
    def fallback_enabled(self) -> bool:
        """Check if fallback is enabled."""
        return self._fallback_enabled
    
    @fallback_enabled.setter
    def fallback_enabled(self, value: bool) -> None:
        """Enable or disable fallback."""
        self._fallback_enabled = value
    
    @property
    def fallback_provider(self) -> Optional[ProviderType]:
        """Get the fallback provider type."""
        return self._fallback_provider
    
    def normalize_symbol(
        self,
        symbol: str,
        target_provider: ProviderType,
    ) -> str:
        """
        Normalize symbol for a specific provider.
        
        Converts between CoinGecko IDs (e.g., 'bitcoin') and
        Bitget trading pairs (e.g., 'BTCUSDT').
        
        Args:
            symbol: Input symbol in any format
            target_provider: Provider to normalize for
            
        Returns:
            Symbol in correct format for target provider
        """
        symbol_lower = symbol.lower()
        symbol_upper = symbol.upper()
        
        if target_provider == ProviderType.BITGET:
            # Convert CoinGecko ID to Bitget pair
            if symbol_lower in COINGECKO_TO_BITGET_MAP:
                return COINGECKO_TO_BITGET_MAP[symbol_lower]
            # Already in Bitget format or unknown
            return symbol_upper if not symbol_upper.endswith("USDT") else symbol_upper
        
        elif target_provider == ProviderType.COINGECKO:
            # Convert Bitget pair to CoinGecko ID
            if symbol_upper in BITGET_TO_COINGECKO_MAP:
                return BITGET_TO_COINGECKO_MAP[symbol_upper]
            # Already in CoinGecko format or unknown
            return symbol_lower
        
        return symbol
    
    def _get_with_fallback(
        self,
        operation: str,
        symbol: str,
        provider: Optional[ProviderType],
        **kwargs,
    ) -> Any:
        """
        Execute an operation with automatic fallback on failure.
        
        Args:
            operation: Method name to call on provider (e.g., 'get_ticker')
            symbol: Trading symbol
            provider: Explicitly requested provider (no fallback if set)
            **kwargs: Additional arguments for the operation
            
        Returns:
            Result from successful provider call
            
        Raises:
            Exception: If all providers fail
        """
        # If explicit provider requested, use it without fallback
        if provider is not None:
            target_provider = self.get_provider(provider)
            normalized_symbol = self.normalize_symbol(symbol, provider)
            method = getattr(target_provider, operation)
            return method(normalized_symbol, **kwargs)
        
        # Try default provider first (Bitget)
        default_pt = self._default_provider or ProviderType.BITGET
        errors = []
        
        if default_pt in self._providers:
            try:
                target_provider = self._providers[default_pt]
                normalized_symbol = self.normalize_symbol(symbol, default_pt)
                method = getattr(target_provider, operation)
                result = method(normalized_symbol, **kwargs)
                logger.debug(f"Successfully fetched {operation} for {symbol} from {default_pt.value}")
                return result
            except Exception as e:
                errors.append(f"{default_pt.value}: {str(e)}")
                logger.warning(f"Default provider {default_pt.value} failed for {symbol}: {e}")
        
        # Fallback to secondary provider if enabled
        if self._fallback_enabled and self._fallback_provider in self._providers:
            fallback_pt = self._fallback_provider
            if fallback_pt != default_pt:  # Don't retry same provider
                try:
                    target_provider = self._providers[fallback_pt]
                    normalized_symbol = self.normalize_symbol(symbol, fallback_pt)
                    method = getattr(target_provider, operation)
                    result = method(normalized_symbol, **kwargs)
                    logger.info(f"Fallback to {fallback_pt.value} succeeded for {symbol}")
                    return result
                except Exception as e:
                    errors.append(f"{fallback_pt.value}: {str(e)}")
                    logger.warning(f"Fallback provider {fallback_pt.value} also failed: {e}")
        
        # All providers failed
        error_msg = f"All providers failed for {operation}({symbol}): " + "; ".join(errors)
        raise RuntimeError(error_msg)
    
    # ==================== Market Data Operations ====================
    
    def get_ticker(
        self,
        symbol: str,
        provider: Optional[ProviderType] = None,
    ) -> TickerData:
        """
        Get ticker data with automatic fallback.
        
        Uses Bitget by default, falls back to CoinGecko if Bitget fails.
        If provider is explicitly specified, no fallback is used.
        
        Args:
            symbol: Trading pair or coin symbol
            provider: Specific provider to use (optional, no fallback if set)
            
        Returns:
            TickerData from the provider
        """
        return self._get_with_fallback("get_ticker", symbol, provider)
    
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
        Get candlestick data with automatic fallback.
        
        Uses Bitget by default for real-time candle data.
        
        Args:
            symbol: Trading pair or coin symbol
            interval: Candle interval
            limit: Maximum candles to return
            provider: Specific provider to use (optional, no fallback if set)
            start_time: Start time for historical data
            end_time: End time for historical data
            
        Returns:
            List of CandleData objects
        """
        return self._get_with_fallback(
            "get_candles", symbol, provider,
            interval=interval, limit=limit,
            start_time=start_time, end_time=end_time
        )
    
    def get_orderbook(
        self,
        symbol: str,
        limit: int = 50,
        provider: Optional[ProviderType] = None,
    ) -> OrderBookData:
        """
        Get order book from a provider that supports it.
        
        Note: Order book is only available from Bitget (not CoinGecko).
        No fallback is used for this operation.
        
        Args:
            symbol: Trading pair
            limit: Number of levels
            provider: Specific provider to use (defaults to Bitget)
            
        Returns:
            OrderBookData with bids and asks
        """
        # Order book is Bitget-specific, no fallback
        target = provider or ProviderType.BITGET
        normalized_symbol = self.normalize_symbol(symbol, target)
        return self.get_provider(target).get_orderbook(normalized_symbol, limit)
    
    def get_recent_trades(
        self,
        symbol: str,
        limit: int = 100,
        provider: Optional[ProviderType] = None,
    ) -> List[TradeData]:
        """
        Get recent trades from a provider that supports it.
        
        Note: Recent trades is only available from Bitget (not CoinGecko).
        No fallback is used for this operation.
        
        Args:
            symbol: Trading pair
            limit: Maximum trades to return
            provider: Specific provider to use (defaults to Bitget)
            
        Returns:
            List of TradeData objects
        """
        # Recent trades is Bitget-specific, no fallback
        target = provider or ProviderType.BITGET
        normalized_symbol = self.normalize_symbol(symbol, target)
        return self.get_provider(target).get_recent_trades(normalized_symbol, limit)
    
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
    fallback_enabled: bool = True,
) -> ExchangeManager:
    """
    Create a pre-configured ExchangeManager with Bitget as default.
    
    Args:
        include_coingecko: Register CoinGecko provider
        include_bitget: Register Bitget provider (from env vars)
        default_provider: Override default provider (defaults to BITGET)
        fallback_enabled: Enable automatic fallback to CoinGecko
        
    Returns:
        Configured ExchangeManager instance
    """
    from .coingecko_provider import CoinGeckoProvider
    from .bitget_provider import BitgetProvider
    
    manager = ExchangeManager(
        default_provider=default_provider,
        fallback_enabled=fallback_enabled,
    )
    
    # Register Bitget FIRST (as primary provider)
    if include_bitget:
        try:
            bitget = BitgetProvider.from_env()
            manager.register_provider(ProviderType.BITGET, bitget)
            logger.info(f"Bitget provider registered (authenticated: {bitget.is_authenticated})")
        except Exception as e:
            logger.warning(f"Could not initialize Bitget provider: {e}")
    
    # Register CoinGecko as fallback
    if include_coingecko:
        manager.register_provider(ProviderType.COINGECKO, CoinGeckoProvider())
        logger.info("CoinGecko provider registered (fallback)")
    
    # Set default to Bitget if available, otherwise CoinGecko
    if default_provider:
        try:
            manager.set_default_provider(default_provider)
        except ValueError:
            pass  # Provider not available
    elif ProviderType.BITGET in manager.available_providers:
        manager.set_default_provider(ProviderType.BITGET)
    elif ProviderType.COINGECKO in manager.available_providers:
        manager.set_default_provider(ProviderType.COINGECKO)
    
    logger.info(f"ExchangeManager ready: default={manager.default_provider}, fallback={manager.fallback_enabled}")
    return manager
