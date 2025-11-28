"""
Exchange Providers Module

This module provides a unified interface for interacting with different
cryptocurrency exchanges. It implements a provider pattern that allows
easy addition of new exchanges while maintaining a consistent API.

Available Providers:
- CoinGeckoProvider: Free public data (prices, market info, historical data)
- BitgetProvider: Professional exchange API (real-time data, trading, futures)

Usage:
    from exchange_providers import ExchangeManager, ProviderType
    
    manager = ExchangeManager()
    manager.register_provider(ProviderType.COINGECKO, CoinGeckoProvider())
    manager.register_provider(ProviderType.BITGET, BitgetProvider.from_env())
    
    # Get data from specific provider
    price = manager.get_ticker("BTCUSDT", provider=ProviderType.BITGET)
    
    # Get aggregated data from all providers
    prices = manager.get_ticker_all_providers("BTCUSDT")
"""

from .base import (
    ExchangeProvider,
    ProviderType,
    TickerData,
    CandleData,
    OrderBookData,
    TradeData,
    AccountBalance,
)
from .coingecko_provider import CoinGeckoProvider
from .bitget_provider import BitgetProvider
from .manager import ExchangeManager

__all__ = [
    # Base classes and types
    "ExchangeProvider",
    "ProviderType",
    "TickerData",
    "CandleData",
    "OrderBookData",
    "TradeData",
    "AccountBalance",
    # Providers
    "CoinGeckoProvider",
    "BitgetProvider",
    # Manager
    "ExchangeManager",
]
