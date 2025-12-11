"""
Exchange Providers Module

This module provides a unified interface for interacting with different
cryptocurrency exchanges and stock market data providers. It implements 
a provider pattern that allows easy addition of new exchanges while 
maintaining a consistent API.

Available Providers:
- CoinGeckoProvider: Free public crypto data (prices, market info, historical data)
- BitgetProvider: Professional crypto exchange API (real-time data, trading, futures)
- YahooFinanceProvider: Stock market data (prices, fundamentals, historical data)

Usage:
    from exchange_providers import ExchangeManager, ProviderType, AssetType
    
    manager = ExchangeManager()
    manager.register_provider(ProviderType.COINGECKO, CoinGeckoProvider())
    manager.register_provider(ProviderType.BITGET, BitgetProvider.from_env())
    manager.register_provider(ProviderType.YAHOO_FINANCE, YahooFinanceProvider())
    
    # Get crypto data
    btc_price = manager.get_ticker("BTCUSDT", provider=ProviderType.BITGET)
    
    # Get stock data
    aapl_price = manager.get_ticker("AAPL", provider=ProviderType.YAHOO_FINANCE)
"""

from .base import (
    ExchangeProvider,
    ProviderType,
    AssetType,
    TickerData,
    CandleData,
    OrderBookData,
    TradeData,
    AccountBalance,
)
from .coingecko_provider import CoinGeckoProvider
from .bitget_provider import BitgetProvider
from .yahoo_finance_provider import YahooFinanceProvider
from .manager import ExchangeManager

__all__ = [
    # Base classes and types
    "ExchangeProvider",
    "ProviderType",
    "AssetType",
    "TickerData",
    "CandleData",
    "OrderBookData",
    "TradeData",
    "AccountBalance",
    # Providers
    "CoinGeckoProvider",
    "BitgetProvider",
    "YahooFinanceProvider",
    # Manager
    "ExchangeManager",
]
