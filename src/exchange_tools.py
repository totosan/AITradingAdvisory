"""
Exchange Tools for MagenticOne Agents

This module provides tool functions that agents can use to interact with
cryptocurrency exchanges. It wraps the ExchangeManager to provide
Annotated function signatures compatible with function calling.

**DEFAULT BEHAVIOR:**
- All tools use Bitget as the PRIMARY data source
- CoinGecko is used as automatic FALLBACK when Bitget fails
- Users can explicitly request a specific provider when needed

Tools:
- get_realtime_price: Get real-time price from Bitget (or fallback)
- get_price_comparison: Compare prices across multiple exchanges
- get_orderbook_depth: Get order book with bid/ask levels
- get_ohlcv_data: Get candlestick/OHLCV data
- get_recent_market_trades: Get recent trade history
- get_futures_data: Get futures-specific data (funding rate, open interest)
- get_account_balance: Get account balances (authenticated)
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Annotated, Optional, List, Literal

from exchange_providers import (
    ExchangeManager,
    ProviderType,
    CoinGeckoProvider,
    BitgetProvider,
)

logger = logging.getLogger(__name__)

# Global exchange manager instance
_exchange_manager: Optional[ExchangeManager] = None


def get_exchange_manager() -> ExchangeManager:
    """
    Get or create the global exchange manager instance.
    
    The manager is configured with:
    - Bitget as PRIMARY provider (real-time data, order books, futures)
    - CoinGecko as FALLBACK provider (broad coin coverage)
    - Automatic fallback enabled by default
    
    Returns:
        Configured ExchangeManager with Bitget as default
    """
    global _exchange_manager
    
    if _exchange_manager is None:
        _exchange_manager = ExchangeManager(
            default_provider=ProviderType.BITGET,
            fallback_enabled=True,
            fallback_provider=ProviderType.COINGECKO,
        )
        
        # Register Bitget FIRST (primary provider)
        try:
            bitget = BitgetProvider.from_env()
            _exchange_manager.register_provider(ProviderType.BITGET, bitget)
            logger.info(f"Bitget provider registered (authenticated: {bitget.is_authenticated})")
        except Exception as e:
            logger.warning(f"Could not initialize Bitget provider: {e}")
        
        # Register CoinGecko as fallback
        _exchange_manager.register_provider(
            ProviderType.COINGECKO,
            CoinGeckoProvider()
        )
        logger.info("CoinGecko provider registered (fallback)")
        
        # Ensure Bitget is default if available
        if ProviderType.BITGET in _exchange_manager.available_providers:
            _exchange_manager.set_default_provider(ProviderType.BITGET)
            logger.info("Default provider set to Bitget")
        else:
            logger.warning("Bitget not available, using CoinGecko as default")
    
    return _exchange_manager


def reset_exchange_manager() -> None:
    """Reset the global exchange manager (for testing)."""
    global _exchange_manager
    _exchange_manager = None


# ==================== Market Data Tools ====================


def get_realtime_price(
    symbol: Annotated[str, "Trading pair symbol (e.g., 'BTCUSDT', 'ETHUSDT', 'bitcoin')"],
    provider: Annotated[Optional[str], "Exchange provider: 'bitget' (default), 'coingecko', or 'auto' (Bitget with fallback)"] = None,
) -> str:
    """
    Get real-time price and market data for a cryptocurrency.
    
    **DEFAULT: Uses Bitget for real-time trading data.**
    Falls back to CoinGecko automatically if Bitget fails.
    
    Use CoinGecko explicitly only when:
    - User specifically requests it
    - Coin is not available on Bitget
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT') or coin ID (e.g., 'bitcoin')
        provider: 'bitget' (default), 'coingecko', or None for auto (Bitget + fallback)
        
    Returns:
        JSON string with current price and market data
        
    Example:
        >>> get_realtime_price("BTCUSDT")  # Uses Bitget
        '{"symbol": "BTCUSDT", "price": 95000.50, "change_24h": 2.5, ...}'
        
        >>> get_realtime_price("bitcoin", provider="coingecko")  # Explicit CoinGecko
        '{"symbol": "bitcoin", "price": 95000.00, ...}'
    """
    try:
        manager = get_exchange_manager()
        
        # Convert provider string to ProviderType
        provider_type = None
        if provider:
            provider_lower = provider.lower()
            if provider_lower == "bitget":
                provider_type = ProviderType.BITGET
            elif provider_lower == "coingecko":
                provider_type = ProviderType.COINGECKO
        
        ticker = manager.get_ticker(symbol, provider=provider_type)
        
        result = {
            "symbol": ticker.symbol,
            "price": ticker.last_price,
            "bid_price": ticker.bid_price,
            "ask_price": ticker.ask_price,
            "spread": (ticker.ask_price - ticker.bid_price) if ticker.bid_price and ticker.ask_price else None,
            "high_24h": ticker.high_24h,
            "low_24h": ticker.low_24h,
            "change_24h_pct": ticker.change_24h,
            "volume_24h_usd": ticker.volume_24h_usd,
            "timestamp": ticker.timestamp.isoformat() if ticker.timestamp else None,
            "provider": ticker.provider,
            **ticker.extra,
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_price_comparison(
    symbol: Annotated[str, "Trading pair symbol (e.g., 'BTCUSDT', 'bitcoin')"],
) -> str:
    """
    Compare cryptocurrency prices across multiple exchanges.
    
    Fetches prices from all registered providers and calculates
    statistics like average price, spread, and arbitrage opportunities.
    
    Args:
        symbol: Trading pair or coin symbol
        
    Returns:
        JSON string with price comparison across exchanges
        
    Example:
        >>> get_price_comparison("BTCUSDT")
        '{"prices": {"Bitget": 95000, "CoinGecko": 94980}, "spread_pct": 0.02, ...}'
    """
    try:
        manager = get_exchange_manager()
        comparison = manager.compare_prices(symbol)
        
        return json.dumps(comparison, indent=2, default=str)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_orderbook_depth(
    symbol: Annotated[str, "Trading pair symbol (e.g., 'BTCUSDT')"],
    limit: Annotated[int, "Number of price levels (1-150, default 20)"] = 20,
) -> str:
    """
    Get order book depth showing buy and sell orders at different price levels.
    
    This tool is only available via Bitget and shows the current market depth
    with bid (buy) and ask (sell) orders. Useful for:
    - Understanding market liquidity
    - Identifying support/resistance levels
    - Detecting large orders (whale activity)
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        limit: Number of price levels to retrieve (default 20, max 150)
        
    Returns:
        JSON string with order book bids and asks
        
    Example:
        >>> get_orderbook_depth("BTCUSDT", limit=10)
        '{"bids": [[94990, 1.5], [94980, 2.3]], "asks": [[95000, 0.8], ...], ...}'
    """
    try:
        manager = get_exchange_manager()
        
        # Order book only available from Bitget
        orderbook = manager.get_orderbook(symbol, limit, provider=ProviderType.BITGET)
        
        result = {
            "symbol": orderbook.symbol,
            "bids": [[b.price, b.size] for b in orderbook.bids[:limit]],
            "asks": [[a.price, a.size] for a in orderbook.asks[:limit]],
            "bid_volume": sum(b.size for b in orderbook.bids),
            "ask_volume": sum(a.size for a in orderbook.asks),
            "spread": orderbook.asks[0].price - orderbook.bids[0].price if orderbook.bids and orderbook.asks else None,
            "timestamp": orderbook.timestamp.isoformat() if orderbook.timestamp else None,
            "provider": orderbook.provider,
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_ohlcv_data(
    symbol: Annotated[str, "Trading pair symbol (e.g., 'BTCUSDT', 'bitcoin')"],
    interval: Annotated[str, "Candle interval: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w"] = "1h",
    limit: Annotated[int, "Number of candles to retrieve (1-1000, default 100)"] = 100,
    provider: Annotated[Optional[str], "Exchange provider: 'bitget' or 'coingecko'"] = None,
) -> str:
    """
    Get OHLCV (Open, High, Low, Close, Volume) candlestick data.
    
    This tool retrieves historical price data in candlestick format,
    useful for technical analysis and charting.
    
    Available intervals:
    - Minutes: 1m, 3m, 5m, 15m, 30m
    - Hours: 1h, 4h, 6h, 12h
    - Days/Weeks: 1d, 3d, 1w, 1M
    
    Args:
        symbol: Trading pair or coin symbol
        interval: Time interval for each candle
        limit: Maximum number of candles (default 100)
        provider: Specific exchange to use (optional)
        
    Returns:
        JSON string with OHLCV data array
        
    Example:
        >>> get_ohlcv_data("BTCUSDT", interval="1h", limit=24)
        '{"symbol": "BTCUSDT", "interval": "1h", "candles": [...], ...}'
    """
    try:
        manager = get_exchange_manager()
        
        # Convert provider string
        provider_type = None
        if provider:
            if provider.lower() == "bitget":
                provider_type = ProviderType.BITGET
            elif provider.lower() == "coingecko":
                provider_type = ProviderType.COINGECKO
        
        candles = manager.get_candles(symbol, interval, limit, provider=provider_type)
        
        # Calculate some basic stats
        if candles:
            closes = [c.close for c in candles]
            highs = [c.high for c in candles]
            lows = [c.low for c in candles]
            volumes = [c.volume for c in candles]
            
            result = {
                "symbol": symbol,
                "interval": interval,
                "count": len(candles),
                "start_time": candles[0].timestamp.isoformat(),
                "end_time": candles[-1].timestamp.isoformat(),
                "statistics": {
                    "current_price": closes[-1],
                    "period_high": max(highs),
                    "period_low": min(lows),
                    "price_change": closes[-1] - closes[0],
                    "price_change_pct": (closes[-1] - closes[0]) / closes[0] * 100,
                    "avg_volume": sum(volumes) / len(volumes),
                    "total_volume": sum(volumes),
                },
                "candles": [c.to_dict() for c in candles],
            }
        else:
            result = {"symbol": symbol, "interval": interval, "count": 0, "candles": []}
        
        return json.dumps(result, indent=2, default=str)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_recent_market_trades(
    symbol: Annotated[str, "Trading pair symbol (e.g., 'BTCUSDT')"],
    limit: Annotated[int, "Number of trades to retrieve (1-500, default 50)"] = 50,
) -> str:
    """
    Get recent market trades for a trading pair.
    
    Shows the most recent executed trades including price, size, and direction.
    Useful for:
    - Understanding current market activity
    - Identifying buying/selling pressure
    - Detecting large trades
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        limit: Maximum number of trades (default 50)
        
    Returns:
        JSON string with recent trade data
        
    Example:
        >>> get_recent_market_trades("BTCUSDT", limit=10)
        '{"trades": [{"price": 95000, "size": 0.5, "side": "buy", ...}], ...}'
    """
    try:
        manager = get_exchange_manager()
        
        # Recent trades only available from Bitget
        trades = manager.get_recent_trades(symbol, limit, provider=ProviderType.BITGET)
        
        # Analyze trade flow
        buy_volume = sum(t.size for t in trades if t.side == "buy")
        sell_volume = sum(t.size for t in trades if t.side == "sell")
        
        result = {
            "symbol": symbol,
            "count": len(trades),
            "analysis": {
                "buy_volume": buy_volume,
                "sell_volume": sell_volume,
                "buy_sell_ratio": buy_volume / sell_volume if sell_volume > 0 else float("inf"),
                "net_flow": buy_volume - sell_volume,
                "pressure": "bullish" if buy_volume > sell_volume else "bearish",
            },
            "trades": [t.to_dict() for t in trades],
        }
        
        return json.dumps(result, indent=2, default=str)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_futures_data(
    symbol: Annotated[str, "Trading pair symbol (e.g., 'BTCUSDT')"],
    product_type: Annotated[str, "Futures type: 'USDT-FUTURES', 'USDC-FUTURES', 'COIN-FUTURES'"] = "USDT-FUTURES",
) -> str:
    """
    Get futures-specific market data including funding rate and open interest.
    
    This tool provides data unique to perpetual futures contracts:
    - Funding rate: Periodic payments between longs and shorts
    - Open interest: Total outstanding contracts
    - Mark price: Fair value price for liquidations
    - Index price: Spot price index
    
    Positive funding rate means longs pay shorts (bullish market).
    Negative funding rate means shorts pay longs (bearish market).
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        product_type: Type of futures contract
        
    Returns:
        JSON string with futures market data
        
    Example:
        >>> get_futures_data("BTCUSDT")
        '{"funding_rate": 0.0001, "open_interest": 50000, "mark_price": 95000, ...}'
    """
    try:
        manager = get_exchange_manager()
        provider = manager.get_provider(ProviderType.BITGET)
        
        if not isinstance(provider, BitgetProvider):
            return json.dumps({"error": "Futures data requires Bitget provider"})
        
        ticker = provider.get_futures_ticker(symbol, product_type)  # type: ignore
        
        result = {
            "symbol": ticker.symbol,
            "last_price": ticker.last_price,
            "mark_price": ticker.extra.get("mark_price"),
            "index_price": ticker.extra.get("index_price"),
            "funding_rate": ticker.extra.get("funding_rate"),
            "funding_rate_pct": ticker.extra.get("funding_rate", 0) * 100 if ticker.extra.get("funding_rate") else None,
            "open_interest": ticker.extra.get("open_interest"),
            "change_24h_pct": ticker.change_24h,
            "volume_24h_usd": ticker.volume_24h_usd,
            "bid_price": ticker.bid_price,
            "ask_price": ticker.ask_price,
            "product_type": product_type,
            "timestamp": ticker.timestamp.isoformat() if ticker.timestamp else None,
            "provider": ticker.provider,
        }
        
        # Add funding rate interpretation
        if ticker.extra.get("funding_rate"):
            fr = ticker.extra["funding_rate"]
            if fr > 0.0001:
                result["funding_interpretation"] = "High positive funding - market is very bullish, longs paying shorts"
            elif fr > 0:
                result["funding_interpretation"] = "Positive funding - market is bullish, longs paying shorts"
            elif fr < -0.0001:
                result["funding_interpretation"] = "High negative funding - market is very bearish, shorts paying longs"
            else:
                result["funding_interpretation"] = "Negative funding - market is bearish, shorts paying longs"
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_futures_candles(
    symbol: Annotated[str, "Trading pair symbol (e.g., 'BTCUSDT')"],
    interval: Annotated[str, "Candle interval: 1m, 5m, 15m, 1h, 4h, 1d"] = "1h",
    limit: Annotated[int, "Number of candles (1-1000, default 100)"] = 100,
    product_type: Annotated[str, "Futures type: 'USDT-FUTURES', 'USDC-FUTURES', 'COIN-FUTURES'"] = "USDT-FUTURES",
) -> str:
    """
    Get OHLCV candlestick data for futures contracts.
    
    Similar to get_ohlcv_data but specifically for futures markets.
    Futures prices may differ slightly from spot due to funding rates.
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        interval: Time interval for each candle
        limit: Maximum number of candles
        product_type: Type of futures contract
        
    Returns:
        JSON string with OHLCV data for futures
    """
    try:
        manager = get_exchange_manager()
        provider = manager.get_provider(ProviderType.BITGET)
        
        if not isinstance(provider, BitgetProvider):
            return json.dumps({"error": "Futures data requires Bitget provider"})
        
        candles = provider.get_futures_candles(symbol, interval, limit, product_type)
        
        if candles:
            closes = [c.close for c in candles]
            
            result = {
                "symbol": symbol,
                "product_type": product_type,
                "interval": interval,
                "count": len(candles),
                "statistics": {
                    "current_price": closes[-1],
                    "period_high": max(c.high for c in candles),
                    "period_low": min(c.low for c in candles),
                    "price_change_pct": (closes[-1] - closes[0]) / closes[0] * 100,
                },
                "candles": [c.to_dict() for c in candles],
            }
        else:
            result = {"symbol": symbol, "interval": interval, "count": 0, "candles": []}
        
        return json.dumps(result, indent=2, default=str)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


# ==================== Account Tools ====================


def get_account_balance(
    coin: Annotated[Optional[str], "Specific coin to query (e.g., 'USDT', 'BTC'), or None for all"] = None,
) -> str:
    """
    Get account balances from Bitget (requires API authentication).
    
    Shows available, frozen, and locked balances for each asset.
    Requires BITGET_API_KEY, BITGET_API_SECRET, and BITGET_PASSPHRASE
    environment variables to be set.
    
    Args:
        coin: Optional specific coin to query
        
    Returns:
        JSON string with account balance information
        
    Example:
        >>> get_account_balance("USDT")
        '{"balances": [{"coin": "USDT", "available": 1000.50, "total": 1050.00}]}'
    """
    try:
        manager = get_exchange_manager()
        provider = manager.get_provider(ProviderType.BITGET)
        
        if not isinstance(provider, BitgetProvider):
            return json.dumps({"error": "Account data requires Bitget provider"})
        
        if not provider.is_authenticated:
            return json.dumps({
                "error": "Authentication required",
                "message": "Set BITGET_API_KEY, BITGET_API_SECRET, and BITGET_PASSPHRASE environment variables"
            })
        
        balances = provider.get_account_balance(coin)
        
        result = {
            "count": len(balances),
            "total_value_estimate": "N/A",  # Would need price data to calculate
            "balances": [b.to_dict() for b in balances],
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


# ==================== Utility Tools ====================


def check_exchange_status() -> str:
    """
    Check the status and health of all configured exchange providers.
    
    Returns information about which providers are available,
    their authentication status, and whether they're responding.
    
    Returns:
        JSON string with provider status information
    """
    try:
        manager = get_exchange_manager()
        
        health = manager.health_check()
        
        result = {
            "default_provider": manager.default_provider.value if manager.default_provider else None,
            "available_providers": [p.value for p in manager.available_providers],
            "health_status": health,
            "provider_details": {},
        }
        
        for provider_type in manager.available_providers:
            provider = manager.get_provider(provider_type)
            result["provider_details"][provider.name] = {
                "type": provider_type.value,
                "requires_auth": provider.requires_auth,
                "supports_futures": provider.supports_futures,
                "supports_trading": provider.supports_trading,
                "is_healthy": health.get(provider.name, False),
            }
            
            # Add auth status for Bitget
            if isinstance(provider, BitgetProvider):
                result["provider_details"][provider.name]["is_authenticated"] = provider.is_authenticated
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


# Export all tool functions
__all__ = [
    # Market data tools
    "get_realtime_price",
    "get_price_comparison",
    "get_orderbook_depth",
    "get_ohlcv_data",
    "get_recent_market_trades",
    "get_futures_data",
    "get_futures_candles",
    # Account tools
    "get_account_balance",
    # Utility tools
    "check_exchange_status",
    # Manager access
    "get_exchange_manager",
    "reset_exchange_manager",
]
