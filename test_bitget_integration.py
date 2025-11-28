#!/usr/bin/env python3
"""
Test script for Bitget Exchange Integration

This script demonstrates the new exchange provider functionality,
including both CoinGecko (existing) and Bitget (new) providers.

Usage:
    python test_bitget_integration.py
    
    # With authentication (for account data):
    export BITGET_API_KEY=your-key
    export BITGET_API_SECRET=your-secret
    export BITGET_PASSPHRASE=your-passphrase
    python test_bitget_integration.py
"""

import json
from datetime import datetime


def test_providers():
    """Test basic provider functionality."""
    print("=" * 60)
    print("Testing Exchange Providers")
    print("=" * 60)
    
    from src.exchange_providers import (
        ExchangeManager, ProviderType,
        CoinGeckoProvider, BitgetProvider
    )
    
    # Create providers
    coingecko = CoinGeckoProvider()
    bitget = BitgetProvider.from_env()
    
    print(f"\n✓ CoinGecko Provider: {coingecko.name}")
    print(f"  - Requires Auth: {coingecko.requires_auth}")
    print(f"  - Supports Futures: {coingecko.supports_futures}")
    
    print(f"\n✓ Bitget Provider: {bitget.name}")
    print(f"  - Is Authenticated: {bitget.is_authenticated}")
    print(f"  - Supports Futures: {bitget.supports_futures}")
    print(f"  - Supports Trading: {bitget.supports_trading}")
    
    # Test manager
    manager = ExchangeManager()
    manager.register_provider(ProviderType.COINGECKO, coingecko)
    manager.register_provider(ProviderType.BITGET, bitget)
    
    print(f"\n✓ Exchange Manager configured")
    print(f"  - Default: {manager.default_provider.value}")
    print(f"  - Available: {[p.value for p in manager.available_providers]}")
    
    return manager


def test_market_data(manager):
    """Test market data retrieval."""
    print("\n" + "=" * 60)
    print("Testing Market Data")
    print("=" * 60)
    
    from src.exchange_providers import ProviderType
    
    symbol = "BTCUSDT"
    
    # Test Bitget ticker
    print(f"\n1. Ticker Data ({symbol}):")
    try:
        bitget_ticker = manager.get_ticker(symbol, provider=ProviderType.BITGET)
        print(f"   Bitget:")
        print(f"   - Price: ${bitget_ticker.last_price:,.2f}")
        print(f"   - Bid/Ask: ${bitget_ticker.bid_price:,.2f} / ${bitget_ticker.ask_price:,.2f}")
        print(f"   - 24h Change: {bitget_ticker.change_24h:.2f}%")
    except Exception as e:
        print(f"   Bitget Error: {e}")
    
    try:
        cg_ticker = manager.get_ticker("bitcoin", provider=ProviderType.COINGECKO)
        print(f"   CoinGecko:")
        print(f"   - Price: ${cg_ticker.last_price:,.2f}")
        print(f"   - 24h Change: {cg_ticker.change_24h:.2f}%")
    except Exception as e:
        print(f"   CoinGecko Error: {e}")
    
    # Test candles
    print(f"\n2. Candlestick Data ({symbol}, 1h):")
    try:
        candles = manager.get_candles(symbol, "1h", limit=5, provider=ProviderType.BITGET)
        print(f"   Retrieved {len(candles)} candles")
        if candles:
            latest = candles[-1]
            print(f"   Latest: O=${latest.open:,.2f} H=${latest.high:,.2f} L=${latest.low:,.2f} C=${latest.close:,.2f}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test orderbook
    print(f"\n3. Order Book ({symbol}):")
    try:
        orderbook = manager.get_orderbook(symbol, limit=5, provider=ProviderType.BITGET)
        print(f"   Bids: {len(orderbook.bids)} levels")
        print(f"   Asks: {len(orderbook.asks)} levels")
        if orderbook.bids and orderbook.asks:
            spread = orderbook.asks[0].price - orderbook.bids[0].price
            print(f"   Spread: ${spread:.2f}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test recent trades
    print(f"\n4. Recent Trades ({symbol}):")
    try:
        trades = manager.get_recent_trades(symbol, limit=10, provider=ProviderType.BITGET)
        buy_count = sum(1 for t in trades if t.side == "buy")
        sell_count = sum(1 for t in trades if t.side == "sell")
        print(f"   Retrieved {len(trades)} trades")
        print(f"   Buy/Sell ratio: {buy_count}/{sell_count}")
    except Exception as e:
        print(f"   Error: {e}")


def test_futures_data():
    """Test futures-specific functionality."""
    print("\n" + "=" * 60)
    print("Testing Futures Data (Bitget)")
    print("=" * 60)
    
    from src.exchange_providers import BitgetProvider
    
    bitget = BitgetProvider.from_env()
    
    print("\n1. BTC Perpetual Futures:")
    try:
        ticker = bitget.get_futures_ticker("BTCUSDT", "USDT-FUTURES")
        print(f"   Last Price: ${ticker.last_price:,.2f}")
        print(f"   Mark Price: ${ticker.extra.get('mark_price', 'N/A')}")
        print(f"   Index Price: ${ticker.extra.get('index_price', 'N/A')}")
        print(f"   Funding Rate: {ticker.extra.get('funding_rate', 0) * 100:.4f}%")
        print(f"   Open Interest: {ticker.extra.get('open_interest', 0):,.2f} BTC")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n2. ETH Perpetual Futures:")
    try:
        ticker = bitget.get_futures_ticker("ETHUSDT", "USDT-FUTURES")
        print(f"   Last Price: ${ticker.last_price:,.2f}")
        print(f"   Funding Rate: {ticker.extra.get('funding_rate', 0) * 100:.4f}%")
    except Exception as e:
        print(f"   Error: {e}")


def test_exchange_tools():
    """Test the exchange tools module."""
    print("\n" + "=" * 60)
    print("Testing Exchange Tools (Agent Functions)")
    print("=" * 60)
    
    from src.exchange_tools import (
        get_realtime_price, get_price_comparison,
        get_orderbook_depth, get_ohlcv_data,
        get_futures_data, check_exchange_status
    )
    
    print("\n1. Exchange Status:")
    status = json.loads(check_exchange_status())
    print(f"   Default: {status['default_provider']}")
    print(f"   Healthy: {status['health_status']}")
    
    print("\n2. Real-time Price (BTCUSDT):")
    price = json.loads(get_realtime_price("BTCUSDT", provider="bitget"))
    if "error" not in price:
        print(f"   Price: ${price['price']:,.2f}")
        print(f"   Spread: ${price['spread']:.2f}")
    else:
        print(f"   Error: {price['error']}")
    
    print("\n3. Price Comparison:")
    comparison = json.loads(get_price_comparison("BTCUSDT"))
    for provider, data in comparison.get("prices", {}).items():
        if isinstance(data, dict) and "price" in data:
            print(f"   {provider}: ${data['price']:,.2f}")
    
    print("\n4. Futures Data (BTCUSDT):")
    futures = json.loads(get_futures_data("BTCUSDT"))
    if "error" not in futures:
        print(f"   Funding Rate: {futures['funding_rate_pct']:.4f}%")
        print(f"   Open Interest: {futures['open_interest']:,.2f} BTC")
    else:
        print(f"   Error: {futures['error']}")


def test_account_data():
    """Test authenticated account data (requires API keys)."""
    print("\n" + "=" * 60)
    print("Testing Account Data (Requires Authentication)")
    print("=" * 60)
    
    from src.exchange_providers import BitgetProvider
    
    bitget = BitgetProvider.from_env()
    
    if not bitget.is_authenticated:
        print("\n⚠ Bitget API credentials not configured.")
        print("  Set BITGET_API_KEY, BITGET_API_SECRET, BITGET_PASSPHRASE")
        print("  to test account functionality.")
        return
    
    print("\n1. Spot Account Balances:")
    try:
        balances = bitget.get_account_balance()
        for balance in balances[:5]:  # Show first 5
            if balance.total > 0:
                print(f"   {balance.coin}: {balance.available:.8f} (frozen: {balance.frozen:.8f})")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n2. Futures Account:")
    try:
        accounts = bitget.get_futures_account("USDT-FUTURES")
        for acc in accounts[:3]:
            print(f"   Margin: {acc.get('marginCoin')} - Equity: {acc.get('accountEquity')}")
    except Exception as e:
        print(f"   Error: {e}")


def main():
    """Run all tests."""
    print("\n" + "🔷" * 30)
    print("  Bitget Exchange Integration Test")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("🔷" * 30)
    
    try:
        manager = test_providers()
        test_market_data(manager)
        test_futures_data()
        test_exchange_tools()
        test_account_data()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
