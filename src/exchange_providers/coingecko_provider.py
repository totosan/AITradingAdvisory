"""
CoinGecko Exchange Provider

This module implements the ExchangeProvider interface for CoinGecko,
providing access to free cryptocurrency market data including prices,
historical data, and market information.

CoinGecko API Documentation:
- Base URL: https://api.coingecko.com/api/v3
- No authentication required (free tier)
- Rate Limits: ~50 calls/minute (free tier)

Note: CoinGecko uses coin IDs (e.g., 'bitcoin') rather than trading pairs.
The provider includes a symbol mapping system to handle conversions.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from .base import (
    ExchangeProvider,
    ProviderType,
    TickerData,
    CandleData,
    OrderBookData,
    TradeData,
    AccountBalance,
)


# Common symbol to CoinGecko ID mapping
SYMBOL_TO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "AVAX": "avalanche-2",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "DOT": "polkadot",
    "MATIC": "matic-network",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "LTC": "litecoin",
    "FTM": "fantom",
    "NEAR": "near",
    "ALGO": "algorand",
    "SUI": "sui",
    "APT": "aptos",
    "ARB": "arbitrum",
    "OP": "optimism",
    "INJ": "injective-protocol",
    "TIA": "celestia",
    "SEI": "sei-network",
    "PEPE": "pepe",
    "SHIB": "shiba-inu",
    "BONK": "bonk",
    "WIF": "dogwifhat",
}


class CoinGeckoProvider(ExchangeProvider):
    """
    CoinGecko exchange provider implementation.
    
    Provides free access to cryptocurrency market data. Note that
    CoinGecko uses coin IDs instead of trading pairs, so symbols
    are automatically converted.
    
    Supported operations:
    - Get ticker data (current price, 24h change, volume)
    - Get historical candlestick data
    - Get detailed market information
    
    Not supported (CoinGecko is data only):
    - Order book
    - Recent trades
    - Account operations
    - Trading
    
    Usage:
        provider = CoinGeckoProvider()
        ticker = provider.get_ticker("bitcoin")  # or "BTC", "BTCUSDT"
        candles = provider.get_candles("ethereum", interval="1d", limit=30)
    """
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self, timeout: int = 15):
        """
        Initialize CoinGecko provider.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self._session = requests.Session()
        self._id_cache: Dict[str, str] = {}
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.COINGECKO
    
    @property
    def name(self) -> str:
        return "CoinGecko"
    
    @property
    def requires_auth(self) -> bool:
        return False
    
    @property
    def supports_futures(self) -> bool:
        return False
    
    @property
    def supports_trading(self) -> bool:
        return False
    
    # ==================== API Request Methods ====================
    
    def _request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Make an API request to CoinGecko.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            Parsed JSON response
            
        Raises:
            ConnectionError: If request fails
            ValueError: If API returns an error
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self._session.get(
                url,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                raise ConnectionError("CoinGecko rate limit exceeded. Please wait and try again.")
            raise ValueError(f"CoinGecko API error: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"CoinGecko API request failed: {str(e)}")
    
    # ==================== Symbol Normalization ====================
    
    def normalize_symbol(self, symbol: str) -> str:
        """
        Convert a symbol to CoinGecko coin ID format.
        
        Handles various input formats:
        - Trading pairs: 'BTCUSDT', 'BTC/USDT', 'BTC-USD'
        - Symbols: 'BTC', 'ETH'
        - CoinGecko IDs: 'bitcoin', 'ethereum'
        
        Args:
            symbol: Input symbol in any format
            
        Returns:
            CoinGecko coin ID (lowercase)
        """
        symbol = symbol.lower().strip()
        
        # If it's already a known CoinGecko ID, return as-is
        if symbol in SYMBOL_TO_ID.values():
            return symbol
        
        # Check cache
        if symbol in self._id_cache:
            return self._id_cache[symbol]
        
        # Remove common quote currencies to extract base symbol
        for suffix in ['usdt', 'usdc', 'usd', 'busd', 'tusd', 'btc', 'eth']:
            if symbol.endswith(suffix) and len(symbol) > len(suffix):
                base = symbol[:-len(suffix)]
                break
        else:
            # Remove separators
            base = symbol.replace('/', '').replace('-', '').replace('_', '')
        
        # Convert to uppercase for mapping lookup
        base_upper = base.upper()
        
        if base_upper in SYMBOL_TO_ID:
            result = SYMBOL_TO_ID[base_upper]
            self._id_cache[symbol] = result
            return result
        
        # Return as-is (lowercase), might be a valid CoinGecko ID
        return base.lower()
    
    # ==================== Market Data ====================
    
    def get_ticker(self, symbol: str) -> TickerData:
        """
        Get current ticker data for a cryptocurrency.
        
        Args:
            symbol: Coin symbol or ID (e.g., 'BTC', 'bitcoin', 'BTCUSDT')
            
        Returns:
            TickerData with current market information
        """
        coin_id = self.normalize_symbol(symbol)
        
        data = self._request(
            "/simple/price",
            params={
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
                "include_24hr_change": "true",
                "include_last_updated_at": "true",
            }
        )
        
        if not data or coin_id not in data:
            raise ValueError(
                f"Cryptocurrency '{symbol}' (resolved to '{coin_id}') not found. "
                "Use CoinGecko IDs like 'bitcoin', 'ethereum', 'solana'"
            )
        
        coin_data = data[coin_id]
        timestamp = None
        if "last_updated_at" in coin_data:
            timestamp = datetime.fromtimestamp(coin_data["last_updated_at"])
        
        return TickerData(
            symbol=coin_id,
            last_price=float(coin_data.get("usd", 0)),
            volume_24h_usd=float(coin_data.get("usd_24h_vol", 0)) if coin_data.get("usd_24h_vol") else None,
            change_24h=float(coin_data.get("usd_24h_change", 0)) if coin_data.get("usd_24h_change") else None,
            timestamp=timestamp,
            provider=self.name,
            extra={
                "market_cap_usd": coin_data.get("usd_market_cap"),
            }
        )
    
    def get_candles(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[CandleData]:
        """
        Get OHLCV candlestick data.
        
        Note: CoinGecko free tier only provides OHLC data, not detailed candles.
        For daily+ granularity, uses market_chart endpoint.
        
        Args:
            symbol: Coin symbol or ID
            interval: Candle interval (CoinGecko supports: 1h, 1d, 7d, 14d, 30d, 90d, 1y, max)
            limit: Maximum candles to return
            start_time: Not used (CoinGecko uses days parameter)
            end_time: Not used
            
        Returns:
            List of CandleData objects
        """
        coin_id = self.normalize_symbol(symbol)
        
        # Map interval to days for CoinGecko
        interval_to_days = {
            "1h": 1,      # Hourly data for 1 day
            "4h": 7,      # 4-hourly data for 7 days
            "1d": 30,     # Daily data for 30 days
            "7d": 90,     # Weekly granularity
            "30d": 365,   # Monthly granularity
        }
        
        days = interval_to_days.get(interval, 30)
        days = min(days, limit)  # Respect limit
        
        data = self._request(
            f"/coins/{coin_id}/market_chart",
            params={
                "vs_currency": "usd",
                "days": days,
                "interval": "daily" if days > 1 else "hourly",
            }
        )
        
        prices = data.get("prices", [])
        
        candles = []
        for i, (timestamp_ms, price) in enumerate(prices[-limit:]):
            # CoinGecko only provides price points, not full OHLC
            # We simulate candles where O=H=L=C=price
            candles.append(CandleData(
                timestamp=datetime.fromtimestamp(timestamp_ms / 1000),
                open=price,
                high=price,
                low=price,
                close=price,
                volume=0,  # Volume not available in this endpoint
            ))
        
        return candles
    
    def get_detailed_market_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get detailed market information for a cryptocurrency.
        
        This is a CoinGecko-specific method that returns comprehensive
        market data not available through the standard interface.
        
        Args:
            symbol: Coin symbol or ID
            
        Returns:
            Dictionary with detailed market data
        """
        coin_id = self.normalize_symbol(symbol)
        
        data = self._request(
            f"/coins/{coin_id}",
            params={
                "localization": "false",
                "tickers": "false",
                "community_data": "true",
                "developer_data": "false",
            }
        )
        
        market_data = data.get("market_data", {})
        
        return {
            "name": data.get("name"),
            "symbol": data.get("symbol", "").upper(),
            "current_price_usd": market_data.get("current_price", {}).get("usd"),
            "market_cap_usd": market_data.get("market_cap", {}).get("usd"),
            "market_cap_rank": market_data.get("market_cap_rank"),
            "total_volume_usd": market_data.get("total_volume", {}).get("usd"),
            "price_change_24h": market_data.get("price_change_percentage_24h"),
            "price_change_7d": market_data.get("price_change_percentage_7d"),
            "price_change_30d": market_data.get("price_change_percentage_30d"),
            "ath_usd": market_data.get("ath", {}).get("usd"),
            "ath_change_percentage": market_data.get("ath_change_percentage", {}).get("usd"),
            "atl_usd": market_data.get("atl", {}).get("usd"),
            "circulating_supply": market_data.get("circulating_supply"),
            "total_supply": market_data.get("total_supply"),
            "max_supply": market_data.get("max_supply"),
            "provider": self.name,
        }
    
    def health_check(self) -> bool:
        """Check if the CoinGecko API is accessible."""
        try:
            self._request("/ping")
            return True
        except Exception:
            return False
