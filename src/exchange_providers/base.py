"""
Base classes and interfaces for exchange providers.

This module defines the abstract base class and data models that all
exchange providers must implement, ensuring a consistent interface
across different platforms.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class ProviderType(Enum):
    """Supported exchange provider types."""
    # Crypto providers
    COINGECKO = "coingecko"
    BITGET = "bitget"
    # Stock providers
    YAHOO_FINANCE = "yahoo_finance"
    # Future providers can be added here
    # BINANCE = "binance"
    # KRAKEN = "kraken"


class AssetType(Enum):
    """Asset type classification for routing."""
    CRYPTO = "crypto"
    STOCK = "stock"
    UNKNOWN = "unknown"


@dataclass
class TickerData:
    """
    Standardized ticker data across all exchanges.
    
    Attributes:
        symbol: Trading pair symbol (e.g., BTCUSDT)
        last_price: Latest trade price
        bid_price: Best bid price
        ask_price: Best ask price
        high_24h: 24-hour high price
        low_24h: 24-hour low price
        volume_24h: 24-hour trading volume in base currency
        volume_24h_usd: 24-hour trading volume in USD
        change_24h: 24-hour price change percentage
        timestamp: Data timestamp
        provider: Source provider name
        extra: Provider-specific additional data
    """
    symbol: str
    last_price: float
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    volume_24h: Optional[float] = None
    volume_24h_usd: Optional[float] = None
    change_24h: Optional[float] = None
    timestamp: Optional[datetime] = None
    provider: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "last_price": self.last_price,
            "bid_price": self.bid_price,
            "ask_price": self.ask_price,
            "high_24h": self.high_24h,
            "low_24h": self.low_24h,
            "volume_24h": self.volume_24h,
            "volume_24h_usd": self.volume_24h_usd,
            "change_24h": self.change_24h,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "provider": self.provider,
            **self.extra
        }


@dataclass
class CandleData:
    """
    OHLCV candlestick data.
    
    Attributes:
        timestamp: Candle open time
        open: Opening price
        high: Highest price
        low: Lowest price
        close: Closing price
        volume: Trading volume in base currency
        volume_usd: Trading volume in USD
    """
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    volume_usd: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "volume_usd": self.volume_usd,
        }


@dataclass
class OrderBookEntry:
    """Single order book entry (bid or ask)."""
    price: float
    size: float


@dataclass
class OrderBookData:
    """
    Order book depth data.
    
    Attributes:
        symbol: Trading pair symbol
        bids: List of bid entries (price, size)
        asks: List of ask entries (price, size)
        timestamp: Data timestamp
        provider: Source provider name
    """
    symbol: str
    bids: List[OrderBookEntry]
    asks: List[OrderBookEntry]
    timestamp: Optional[datetime] = None
    provider: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "bids": [[b.price, b.size] for b in self.bids],
            "asks": [[a.price, a.size] for a in self.asks],
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "provider": self.provider,
        }


@dataclass
class TradeData:
    """
    Recent trade data.
    
    Attributes:
        trade_id: Unique trade identifier
        symbol: Trading pair symbol
        price: Trade price
        size: Trade size
        side: Trade side ('buy' or 'sell')
        timestamp: Trade timestamp
    """
    trade_id: str
    symbol: str
    price: float
    size: float
    side: str  # 'buy' or 'sell'
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "price": self.price,
            "size": self.size,
            "side": self.side,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AccountBalance:
    """
    Account balance for a single asset.
    
    Attributes:
        coin: Asset/coin name
        available: Available balance
        frozen: Frozen balance (in orders)
        locked: Locked balance
        total: Total balance (available + frozen + locked)
    """
    coin: str
    available: float
    frozen: float = 0.0
    locked: float = 0.0
    
    @property
    def total(self) -> float:
        """Calculate total balance."""
        return self.available + self.frozen + self.locked
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "coin": self.coin,
            "available": self.available,
            "frozen": self.frozen,
            "locked": self.locked,
            "total": self.total,
        }


class ExchangeProvider(ABC):
    """
    Abstract base class for cryptocurrency exchange providers.
    
    All exchange implementations must inherit from this class and
    implement the required methods. Optional methods have default
    implementations that raise NotImplementedError.
    """
    
    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Return the provider type identifier."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return human-readable provider name."""
        pass
    
    @property
    def requires_auth(self) -> bool:
        """Return True if this provider requires authentication."""
        return False
    
    @property
    def supports_futures(self) -> bool:
        """Return True if this provider supports futures trading."""
        return False
    
    @property
    def supports_trading(self) -> bool:
        """Return True if this provider supports trading operations."""
        return False
    
    # ==================== Market Data Methods ====================
    
    @abstractmethod
    def get_ticker(self, symbol: str) -> TickerData:
        """
        Get current ticker data for a symbol.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT' or 'bitcoin' depending on provider)
            
        Returns:
            TickerData with current market information
            
        Raises:
            ValueError: If symbol is not found
            ConnectionError: If API request fails
        """
        pass
    
    @abstractmethod
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
        
        Args:
            symbol: Trading pair
            interval: Candle interval (e.g., '1m', '5m', '1h', '1d')
            limit: Maximum number of candles to return
            start_time: Start time for historical data
            end_time: End time for historical data
            
        Returns:
            List of CandleData objects
        """
        pass
    
    def get_orderbook(self, symbol: str, limit: int = 50) -> OrderBookData:
        """
        Get order book depth data.
        
        Args:
            symbol: Trading pair
            limit: Number of levels to return
            
        Returns:
            OrderBookData with bids and asks
            
        Note:
            Not all providers support this. Default raises NotImplementedError.
        """
        raise NotImplementedError(f"{self.name} does not support order book data")
    
    def get_recent_trades(self, symbol: str, limit: int = 100) -> List[TradeData]:
        """
        Get recent trades for a symbol.
        
        Args:
            symbol: Trading pair
            limit: Maximum number of trades to return
            
        Returns:
            List of TradeData objects
            
        Note:
            Not all providers support this. Default raises NotImplementedError.
        """
        raise NotImplementedError(f"{self.name} does not support recent trades")
    
    # ==================== Account Methods ====================
    
    def get_account_balance(self, coin: Optional[str] = None) -> List[AccountBalance]:
        """
        Get account balances.
        
        Args:
            coin: Optional specific coin to query
            
        Returns:
            List of AccountBalance objects
            
        Note:
            Requires authentication. Default raises NotImplementedError.
        """
        raise NotImplementedError(f"{self.name} does not support account data")
    
    # ==================== Utility Methods ====================
    
    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize a symbol to this provider's format.
        
        Different providers use different symbol formats:
        - CoinGecko: 'bitcoin', 'ethereum'
        - Bitget: 'BTCUSDT', 'ETHUSDT'
        
        Args:
            symbol: Input symbol in any format
            
        Returns:
            Symbol in this provider's format
        """
        return symbol
    
    def health_check(self) -> bool:
        """
        Check if the provider API is accessible.
        
        Returns:
            True if API is reachable and responding
        """
        try:
            # Try to get a common ticker as health check
            self.get_ticker(self.normalize_symbol("bitcoin"))
            return True
        except Exception:
            return False
