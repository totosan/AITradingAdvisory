"""
Bitget Exchange Provider

This module implements the ExchangeProvider interface for Bitget exchange,
providing access to spot and futures market data, as well as authenticated
account operations.

Bitget API Documentation:
- Base URL: https://api.bitget.com
- Authentication: HMAC-SHA256 signature
- Rate Limits: 20 requests/second for market data, 10 requests/second for account

Features:
- Spot market data (tickers, candles, orderbook, trades)
- Futures market data (USDT-M, USDC-M, Coin-M futures)
- Account balance and positions (requires API key)
"""

import os
import hmac
import hashlib
import base64
import time
import json
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Literal

from .base import (
    ExchangeProvider,
    ProviderType,
    TickerData,
    CandleData,
    OrderBookData,
    OrderBookEntry,
    TradeData,
    AccountBalance,
)


# Bitget interval mapping
INTERVAL_MAP = {
    "1m": "1min",
    "3m": "3min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "4h": "4h",
    "6h": "6h",
    "12h": "12h",
    "1d": "1day",
    "3d": "3day",
    "1w": "1week",
    "1M": "1M",
}

# Futures interval mapping (slightly different)
FUTURES_INTERVAL_MAP = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1H",
    "4h": "4H",
    "6h": "6H",
    "12h": "12H",
    "1d": "1D",
    "3d": "3D",
    "1w": "1W",
    "1M": "1M",
}

# Product types for futures
ProductType = Literal["USDT-FUTURES", "USDC-FUTURES", "COIN-FUTURES"]


class BitgetAuthError(Exception):
    """Raised when authentication fails."""
    pass


class BitgetAPIError(Exception):
    """Raised when API request fails."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Bitget API Error {code}: {message}")


class BitgetProvider(ExchangeProvider):
    """
    Bitget exchange provider implementation.
    
    Supports both public (no auth) and private (requires auth) endpoints.
    
    Public endpoints:
    - Market tickers
    - Candlestick/OHLCV data
    - Order book depth
    - Recent trades
    
    Private endpoints (requires API key):
    - Account balance
    - Position data
    - Order management
    
    Usage:
        # Public data only
        provider = BitgetProvider()
        ticker = provider.get_ticker("BTCUSDT")
        
        # With authentication
        provider = BitgetProvider.from_env()  # Uses BITGET_API_KEY, etc.
        balance = provider.get_account_balance()
    """
    
    BASE_URL = "https://api.bitget.com"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        timeout: int = 10,
    ):
        """
        Initialize Bitget provider.
        
        Args:
            api_key: Bitget API key (optional for public endpoints)
            api_secret: Bitget API secret (optional for public endpoints)
            passphrase: Bitget API passphrase (optional for public endpoints)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.timeout = timeout
        self._session = requests.Session()
    
    @classmethod
    def from_env(cls) -> "BitgetProvider":
        """
        Create provider from environment variables.
        
        Environment variables:
        - BITGET_API_KEY: API key
        - BITGET_API_SECRET: API secret
        - BITGET_PASSPHRASE: API passphrase
        - BITGET_TIMEOUT: Request timeout (optional, default 10)
        
        Returns:
            Configured BitgetProvider instance
        """
        api_key = os.getenv("BITGET_API_KEY")
        api_secret = os.getenv("BITGET_API_SECRET")
        passphrase = os.getenv("BITGET_PASSPHRASE")
        timeout = int(os.getenv("BITGET_TIMEOUT", "10"))
        
        return cls(
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            timeout=timeout,
        )
    
    @classmethod
    def from_vault(cls, vault) -> "BitgetProvider":
        """
        Create provider from SecretsVault credentials.
        
        This method attempts to load credentials from the vault first,
        falling back to environment variables if vault secrets are not available.
        
        Args:
            vault: SecretsVault instance
            
        Returns:
            Configured BitgetProvider instance
        """
        api_key = None
        api_secret = None
        passphrase = None
        
        # Try vault first
        if vault is not None:
            try:
                api_key = vault.get_secret("bitget_api_key")
                api_secret = vault.get_secret("bitget_api_secret")
                passphrase = vault.get_secret("bitget_passphrase")
            except Exception:
                pass
        
        # Fallback to environment variables if vault doesn't have credentials
        if not api_key:
            api_key = os.getenv("BITGET_API_KEY")
        if not api_secret:
            api_secret = os.getenv("BITGET_API_SECRET")
        if not passphrase:
            passphrase = os.getenv("BITGET_PASSPHRASE")
        
        timeout = int(os.getenv("BITGET_TIMEOUT", "10"))
        
        return cls(
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            timeout=timeout,
        )
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.BITGET
    
    @property
    def name(self) -> str:
        return "Bitget"
    
    @property
    def requires_auth(self) -> bool:
        return False  # Public endpoints work without auth
    
    @property
    def supports_futures(self) -> bool:
        return True
    
    @property
    def supports_trading(self) -> bool:
        return self.is_authenticated
    
    @property
    def is_authenticated(self) -> bool:
        """Check if API credentials are configured."""
        return all([self.api_key, self.api_secret, self.passphrase])
    
    # ==================== Authentication ====================
    
    def _generate_signature(
        self,
        timestamp: str,
        method: str,
        request_path: str,
        body: str = "",
        query_string: str = "",
    ) -> str:
        """
        Generate HMAC-SHA256 signature for authenticated requests.
        
        Signature = Base64(HMAC-SHA256(timestamp + method + requestPath + queryString + body))
        
        Args:
            timestamp: Millisecond timestamp
            method: HTTP method (GET/POST)
            request_path: API endpoint path
            body: Request body (for POST requests)
            query_string: Query parameters (for GET requests)
            
        Returns:
            Base64-encoded signature
        """
        if not self.api_secret:
            raise BitgetAuthError("API secret not configured")
        
        # Build message to sign
        if query_string:
            message = f"{timestamp}{method.upper()}{request_path}?{query_string}{body}"
        else:
            message = f"{timestamp}{method.upper()}{request_path}{body}"
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        # Base64 encode
        return base64.b64encode(signature).decode('utf-8')
    
    def _get_headers(
        self,
        method: str,
        request_path: str,
        body: str = "",
        query_string: str = "",
    ) -> Dict[str, str]:
        """
        Generate request headers including authentication if available.
        
        Args:
            method: HTTP method
            request_path: API endpoint path
            body: Request body
            query_string: Query parameters
            
        Returns:
            Headers dictionary
        """
        headers = {
            "Content-Type": "application/json",
            "locale": "en-US",
        }
        
        if self.is_authenticated:
            timestamp = str(int(time.time() * 1000))
            signature = self._generate_signature(
                timestamp, method, request_path, body, query_string
            )
            
            headers.update({
                "ACCESS-KEY": self.api_key,
                "ACCESS-SIGN": signature,
                "ACCESS-TIMESTAMP": timestamp,
                "ACCESS-PASSPHRASE": self.passphrase,
            })
        
        return headers
    
    # ==================== API Request Methods ====================
    
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        auth_required: bool = False,
    ) -> Dict[str, Any]:
        """
        Make an API request to Bitget.
        
        Args:
            method: HTTP method (GET/POST)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body data
            auth_required: Whether authentication is required
            
        Returns:
            Parsed JSON response data
            
        Raises:
            BitgetAuthError: If auth required but not configured
            BitgetAPIError: If API returns an error
            ConnectionError: If request fails
        """
        if auth_required and not self.is_authenticated:
            raise BitgetAuthError(
                "Authentication required. Configure BITGET_API_KEY, "
                "BITGET_API_SECRET, and BITGET_PASSPHRASE"
            )
        
        url = f"{self.BASE_URL}{endpoint}"
        query_string = ""
        body = ""
        
        if params:
            query_string = "&".join(f"{k}={v}" for k, v in params.items())
        
        if data:
            body = json.dumps(data)
        
        headers = self._get_headers(method, endpoint, body, query_string)
        
        try:
            if method.upper() == "GET":
                response = self._session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                )
            else:
                response = self._session.post(
                    url,
                    json=data,
                    headers=headers,
                    timeout=self.timeout,
                )
            
            response.raise_for_status()
            result = response.json()
            
            # Check for API error
            if result.get("code") != "00000":
                raise BitgetAPIError(
                    result.get("code", "unknown"),
                    result.get("msg", "Unknown error")
                )
            
            return result.get("data", result)
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Bitget API request failed: {str(e)}")
    
    # ==================== Spot Market Data ====================
    
    def get_ticker(self, symbol: str) -> TickerData:
        """
        Get current ticker data for a spot trading pair.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            
        Returns:
            TickerData with current market information
        """
        symbol = self.normalize_symbol(symbol)
        
        data = self._request(
            "GET",
            "/api/v2/spot/market/tickers",
            params={"symbol": symbol}
        )
        
        if not data:
            raise ValueError(f"Symbol '{symbol}' not found")
        
        ticker = data[0] if isinstance(data, list) else data
        
        return TickerData(
            symbol=ticker.get("symbol", symbol),
            last_price=float(ticker.get("lastPr", 0)),
            bid_price=float(ticker.get("bidPr", 0)) if ticker.get("bidPr") else None,
            ask_price=float(ticker.get("askPr", 0)) if ticker.get("askPr") else None,
            high_24h=float(ticker.get("high24h", 0)) if ticker.get("high24h") else None,
            low_24h=float(ticker.get("low24h", 0)) if ticker.get("low24h") else None,
            volume_24h=float(ticker.get("baseVolume", 0)) if ticker.get("baseVolume") else None,
            volume_24h_usd=float(ticker.get("usdtVolume", 0)) if ticker.get("usdtVolume") else None,
            change_24h=float(ticker.get("change24h", 0)) * 100 if ticker.get("change24h") else None,
            timestamp=datetime.fromtimestamp(int(ticker.get("ts", 0)) / 1000) if ticker.get("ts") else None,
            provider=self.name,
            extra={
                "open_24h": float(ticker.get("open", 0)) if ticker.get("open") else None,
                "quote_volume": float(ticker.get("quoteVolume", 0)) if ticker.get("quoteVolume") else None,
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
        Get OHLCV candlestick data for a spot trading pair.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Candle interval (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            limit: Maximum candles to return (default 100, max 1000)
            start_time: Start time for historical data
            end_time: End time for historical data
            
        Returns:
            List of CandleData objects
        """
        symbol = self.normalize_symbol(symbol)
        granularity = INTERVAL_MAP.get(interval, interval)
        
        params = {
            "symbol": symbol,
            "granularity": granularity,
            "limit": str(min(limit, 1000)),
        }
        
        if start_time:
            params["startTime"] = str(int(start_time.timestamp() * 1000))
        if end_time:
            params["endTime"] = str(int(end_time.timestamp() * 1000))
        
        data = self._request("GET", "/api/v2/spot/market/candles", params=params)
        
        candles = []
        for item in data:
            # Bitget returns: [timestamp, open, high, low, close, volume, volume_usdt, volume_quote]
            candles.append(CandleData(
                timestamp=datetime.fromtimestamp(int(item[0]) / 1000),
                open=float(item[1]),
                high=float(item[2]),
                low=float(item[3]),
                close=float(item[4]),
                volume=float(item[5]),
                volume_usd=float(item[6]) if len(item) > 6 else None,
            ))
        
        return candles
    
    def get_orderbook(self, symbol: str, limit: int = 50) -> OrderBookData:
        """
        Get order book depth for a spot trading pair.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            limit: Number of levels (max 150)
            
        Returns:
            OrderBookData with bids and asks
        """
        symbol = self.normalize_symbol(symbol)
        
        data = self._request(
            "GET",
            "/api/v2/spot/market/orderbook",
            params={
                "symbol": symbol,
                "limit": str(min(limit, 150)),
            }
        )
        
        bids = [
            OrderBookEntry(price=float(b[0]), size=float(b[1]))
            for b in data.get("bids", [])
        ]
        asks = [
            OrderBookEntry(price=float(a[0]), size=float(a[1]))
            for a in data.get("asks", [])
        ]
        
        return OrderBookData(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=datetime.fromtimestamp(int(data.get("ts", 0)) / 1000) if data.get("ts") else None,
            provider=self.name,
        )
    
    def get_recent_trades(self, symbol: str, limit: int = 100) -> List[TradeData]:
        """
        Get recent trades for a spot trading pair.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            limit: Maximum trades to return (max 500)
            
        Returns:
            List of TradeData objects
        """
        symbol = self.normalize_symbol(symbol)
        
        data = self._request(
            "GET",
            "/api/v2/spot/market/fills",
            params={
                "symbol": symbol,
                "limit": str(min(limit, 500)),
            }
        )
        
        trades = []
        for item in data:
            trades.append(TradeData(
                trade_id=item.get("tradeId", ""),
                symbol=item.get("symbol", symbol),
                price=float(item.get("price", 0)),
                size=float(item.get("size", 0)),
                side=item.get("side", "").lower(),
                timestamp=datetime.fromtimestamp(int(item.get("ts", 0)) / 1000),
            ))
        
        return trades
    
    # ==================== Futures Market Data ====================
    
    def get_futures_ticker(
        self,
        symbol: str,
        product_type: ProductType = "USDT-FUTURES",
    ) -> TickerData:
        """
        Get current ticker data for a futures contract.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            product_type: Futures type (USDT-FUTURES, USDC-FUTURES, COIN-FUTURES)
            
        Returns:
            TickerData with current market information including funding rate
        """
        symbol = self.normalize_symbol(symbol)
        
        data = self._request(
            "GET",
            "/api/v2/mix/market/ticker",
            params={
                "symbol": symbol,
                "productType": product_type,
            }
        )
        
        if not data:
            raise ValueError(f"Futures symbol '{symbol}' not found")
        
        ticker = data[0] if isinstance(data, list) else data
        
        return TickerData(
            symbol=ticker.get("symbol", symbol),
            last_price=float(ticker.get("lastPr", 0)),
            bid_price=float(ticker.get("bidPr", 0)) if ticker.get("bidPr") else None,
            ask_price=float(ticker.get("askPr", 0)) if ticker.get("askPr") else None,
            high_24h=float(ticker.get("high24h", 0)) if ticker.get("high24h") else None,
            low_24h=float(ticker.get("low24h", 0)) if ticker.get("low24h") else None,
            volume_24h=float(ticker.get("baseVolume", 0)) if ticker.get("baseVolume") else None,
            volume_24h_usd=float(ticker.get("usdtVolume", 0)) if ticker.get("usdtVolume") else None,
            change_24h=float(ticker.get("change24h", 0)) * 100 if ticker.get("change24h") else None,
            timestamp=datetime.fromtimestamp(int(ticker.get("ts", 0)) / 1000) if ticker.get("ts") else None,
            provider=self.name,
            extra={
                "index_price": float(ticker.get("indexPrice", 0)) if ticker.get("indexPrice") else None,
                "mark_price": float(ticker.get("markPrice", 0)) if ticker.get("markPrice") else None,
                "funding_rate": float(ticker.get("fundingRate", 0)) if ticker.get("fundingRate") else None,
                "open_interest": float(ticker.get("holdingAmount", 0)) if ticker.get("holdingAmount") else None,
                "product_type": product_type,
            }
        )
    
    def get_futures_candles(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100,
        product_type: ProductType = "USDT-FUTURES",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[CandleData]:
        """
        Get OHLCV candlestick data for a futures contract.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Candle interval (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            limit: Maximum candles to return (default 100, max 1000)
            product_type: Futures type
            start_time: Start time for historical data
            end_time: End time for historical data
            
        Returns:
            List of CandleData objects
        """
        symbol = self.normalize_symbol(symbol)
        granularity = FUTURES_INTERVAL_MAP.get(interval, interval)
        
        params = {
            "symbol": symbol,
            "productType": product_type,
            "granularity": granularity,
            "limit": str(min(limit, 1000)),
        }
        
        if start_time:
            params["startTime"] = str(int(start_time.timestamp() * 1000))
        if end_time:
            params["endTime"] = str(int(end_time.timestamp() * 1000))
        
        data = self._request("GET", "/api/v2/mix/market/candles", params=params)
        
        candles = []
        for item in data:
            # Bitget futures returns: [timestamp, open, high, low, close, volume, quote_volume]
            candles.append(CandleData(
                timestamp=datetime.fromtimestamp(int(item[0]) / 1000),
                open=float(item[1]),
                high=float(item[2]),
                low=float(item[3]),
                close=float(item[4]),
                volume=float(item[5]),
                volume_usd=float(item[6]) if len(item) > 6 else None,
            ))
        
        return candles
    
    # ==================== Account Data ====================
    
    def get_account_balance(self, coin: Optional[str] = None) -> List[AccountBalance]:
        """
        Get spot account balances.
        
        Args:
            coin: Optional specific coin to query
            
        Returns:
            List of AccountBalance objects
            
        Raises:
            BitgetAuthError: If not authenticated
        """
        params = {}
        if coin:
            params["coin"] = coin.upper()
        else:
            params["assetType"] = "hold_only"
        
        data = self._request(
            "GET",
            "/api/v2/spot/account/assets",
            params=params,
            auth_required=True,
        )
        
        balances = []
        for item in data:
            balances.append(AccountBalance(
                coin=item.get("coin", "").upper(),
                available=float(item.get("available", 0)),
                frozen=float(item.get("frozen", 0)),
                locked=float(item.get("locked", 0)),
            ))
        
        return balances
    
    def get_futures_account(
        self,
        product_type: ProductType = "USDT-FUTURES",
    ) -> List[Dict[str, Any]]:
        """
        Get futures account information.
        
        Args:
            product_type: Futures type
            
        Returns:
            List of account dictionaries with margin info
            
        Raises:
            BitgetAuthError: If not authenticated
        """
        data = self._request(
            "GET",
            "/api/v2/mix/account/accounts",
            params={"productType": product_type},
            auth_required=True,
        )
        
        return data
    
    # ==================== Utility Methods ====================
    
    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize a symbol to Bitget format.
        
        Examples:
            'btcusdt' -> 'BTCUSDT'
            'BTC/USDT' -> 'BTCUSDT'
            'btc-usdt' -> 'BTCUSDT'
        """
        # Remove common separators and uppercase
        return symbol.upper().replace("/", "").replace("-", "").replace("_", "")
    
    def health_check(self) -> bool:
        """Check if the Bitget API is accessible."""
        try:
            self._request("GET", "/api/v2/spot/market/tickers", params={"symbol": "BTCUSDT"})
            return True
        except Exception:
            return False
