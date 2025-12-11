"""
Yahoo Finance Provider for Stock Market Data

This module implements the ExchangeProvider interface for Yahoo Finance,
providing access to stock market data including prices, historical data,
and company information.

Uses yfinance library for data access (unofficial Yahoo Finance API).

Supported operations:
- Get ticker data (current price, 24h change, volume)
- Get historical candlestick data
- Get company fundamentals and info

Not supported (Yahoo Finance is data only):
- Order book
- Recent trades
- Account operations
- Trading
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

try:
    import yfinance as yf
except ImportError:
    yf = None

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


# Popular stock symbols for recognition
POPULAR_STOCKS = {
    # US Tech Giants
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA",
    "AMD", "INTC", "CRM", "ORCL", "IBM", "CSCO", "ADBE", "NFLX",
    # US Finance
    "JPM", "BAC", "WFC", "GS", "MS", "V", "MA", "PYPL",
    # US Industrial & Consumer
    "DIS", "NKE", "MCD", "KO", "PEP", "WMT", "HD", "BA", "CAT",
    # German Stocks (XETRA)
    "SAP", "SIE", "ALV", "DTE", "BAYN", "BMW", "MBG", "VOW3",
    "ADS", "BAS", "DB1", "DBK", "DPW", "FRE", "HEI", "IFX",
    "LIN", "MRK", "MUV2", "RWE", "VNA", "ZAL",
    # ETFs
    "SPY", "QQQ", "DIA", "IWM", "VTI", "VOO", "ARKK", "XLF", "XLE",
    # Indices (as tickers)
    "^GSPC", "^DJI", "^IXIC", "^GDAXI", "^FTSE",
}

# Common stock name to symbol mapping
STOCK_NAME_TO_SYMBOL = {
    "APPLE": "AAPL",
    "MICROSOFT": "MSFT",
    "GOOGLE": "GOOGL",
    "ALPHABET": "GOOGL",
    "AMAZON": "AMZN",
    "FACEBOOK": "META",
    "META": "META",
    "NVIDIA": "NVDA",
    "TESLA": "TSLA",
    "AMD": "AMD",
    "INTEL": "INTC",
    "NETFLIX": "NFLX",
    "DISNEY": "DIS",
    "COCA-COLA": "KO",
    "COCA COLA": "KO",
    "PEPSI": "PEP",
    "MCDONALDS": "MCD",
    "NIKE": "NKE",
    "WALMART": "WMT",
    "BOEING": "BA",
    "VISA": "V",
    "MASTERCARD": "MA",
    "PAYPAL": "PYPL",
    "JPMORGAN": "JPM",
    "GOLDMAN": "GS",
    "GOLDMAN SACHS": "GS",
    # German companies
    "SIEMENS": "SIE.DE",
    "SAP": "SAP.DE",
    "BAYER": "BAYN.DE",
    "BMW": "BMW.DE",
    "MERCEDES": "MBG.DE",
    "DAIMLER": "MBG.DE",
    "VOLKSWAGEN": "VOW3.DE",
    "VW": "VOW3.DE",
    "DEUTSCHE BANK": "DBK.DE",
    "ALLIANZ": "ALV.DE",
    "ADIDAS": "ADS.DE",
    "BASF": "BAS.DE",
    "DEUTSCHE TELEKOM": "DTE.DE",
    "TELEKOM": "DTE.DE",
    # Indices
    "S&P 500": "^GSPC",
    "S&P": "^GSPC",
    "DOW JONES": "^DJI",
    "DOW": "^DJI",
    "NASDAQ": "^IXIC",
    "DAX": "^GDAXI",
    "FTSE": "^FTSE",
}


class YahooFinanceProvider(ExchangeProvider):
    """
    Yahoo Finance provider implementation for stock market data.
    
    Provides access to stock, ETF, and index data via yfinance library.
    
    Supported operations:
    - Get ticker data (current price, change, volume)
    - Get historical candlestick data
    - Get company info and fundamentals
    
    Not supported (data only):
    - Order book
    - Real-time trades
    - Account operations
    - Trading
    
    Usage:
        provider = YahooFinanceProvider()
        ticker = provider.get_ticker("AAPL")
        candles = provider.get_candles("MSFT", interval="1d", limit=30)
    """
    
    def __init__(self, timeout: int = 15):
        """
        Initialize Yahoo Finance provider.
        
        Args:
            timeout: Request timeout in seconds
        """
        if yf is None:
            raise ImportError(
                "yfinance package is required for YahooFinanceProvider. "
                "Install with: pip install yfinance"
            )
        self.timeout = timeout
        self._ticker_cache: Dict[str, Any] = {}
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.YAHOO_FINANCE
    
    @property
    def name(self) -> str:
        return "Yahoo Finance"
    
    @property
    def requires_auth(self) -> bool:
        return False
    
    @property
    def supports_futures(self) -> bool:
        return False
    
    @property
    def supports_trading(self) -> bool:
        return False
    
    def _get_yf_ticker(self, symbol: str) -> Any:
        """
        Get or create a yfinance Ticker object.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            yfinance Ticker object
        """
        symbol_upper = symbol.upper()
        if symbol_upper not in self._ticker_cache:
            self._ticker_cache[symbol_upper] = yf.Ticker(symbol_upper)
        return self._ticker_cache[symbol_upper]
    
    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize stock symbol to Yahoo Finance format.
        
        Args:
            symbol: Input symbol (can be company name or ticker)
            
        Returns:
            Normalized ticker symbol
        """
        symbol_upper = symbol.upper().strip()
        
        # Check if it's a known company name
        if symbol_upper in STOCK_NAME_TO_SYMBOL:
            return STOCK_NAME_TO_SYMBOL[symbol_upper]
        
        # Remove common suffixes that might be added
        if symbol_upper.endswith("USD") or symbol_upper.endswith("USDT"):
            symbol_upper = symbol_upper[:-4] if symbol_upper.endswith("USDT") else symbol_upper[:-3]
        
        return symbol_upper
    
    def get_ticker(self, symbol: str) -> TickerData:
        """
        Get current ticker data for a stock.
        
        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
            
        Returns:
            TickerData with current market information
            
        Raises:
            ValueError: If symbol is not found
            ConnectionError: If API request fails
        """
        try:
            normalized = self.normalize_symbol(symbol)
            ticker = self._get_yf_ticker(normalized)
            
            # Get fast info (most current data)
            info = ticker.fast_info
            
            # Get historical data for more details
            hist = ticker.history(period="2d")
            
            if hist.empty:
                raise ValueError(f"No data found for symbol: {symbol}")
            
            last_row = hist.iloc[-1]
            prev_close = hist.iloc[-2]["Close"] if len(hist) > 1 else last_row["Close"]
            
            # Calculate change
            last_price = float(last_row["Close"])
            change_24h = ((last_price - prev_close) / prev_close * 100) if prev_close else 0
            
            return TickerData(
                symbol=normalized,
                last_price=last_price,
                bid_price=None,  # Not available in free Yahoo data
                ask_price=None,
                high_24h=float(last_row["High"]),
                low_24h=float(last_row["Low"]),
                volume_24h=float(last_row["Volume"]),
                volume_24h_usd=float(last_row["Volume"]) * last_price,
                change_24h=change_24h,
                timestamp=datetime.now(),
                provider=self.name,
                extra={
                    "open": float(last_row["Open"]),
                    "previous_close": prev_close,
                    "market_cap": getattr(info, "market_cap", None),
                    "currency": getattr(info, "currency", "USD"),
                    "asset_type": "stock",
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to get ticker for {symbol}: {e}")
            raise ValueError(f"Could not fetch data for symbol '{symbol}': {e}")
    
    def get_candles(
        self,
        symbol: str,
        interval: str = "1d",
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[CandleData]:
        """
        Get OHLCV candlestick data for a stock.
        
        Args:
            symbol: Stock ticker symbol
            interval: Candle interval (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo)
            limit: Maximum number of candles to return
            start_time: Start time for historical data
            end_time: End time for historical data
            
        Returns:
            List of CandleData objects
        """
        try:
            normalized = self.normalize_symbol(symbol)
            ticker = self._get_yf_ticker(normalized)
            
            # Map interval format to yfinance format
            interval_map = {
                "1m": "1m",
                "5m": "5m",
                "15m": "15m",
                "30m": "30m",
                "1h": "1h",
                "4h": "1h",  # 4h not directly supported, use 1h
                "1d": "1d",
                "1w": "1wk",
                "1M": "1mo",
            }
            yf_interval = interval_map.get(interval, "1d")
            
            # Calculate period based on limit and interval
            if start_time and end_time:
                hist = ticker.history(start=start_time, end=end_time, interval=yf_interval)
            else:
                # Determine period based on interval
                if yf_interval in ["1m", "5m", "15m", "30m"]:
                    period = "5d"  # Max for minute data
                elif yf_interval == "1h":
                    period = "60d"
                elif yf_interval == "1d":
                    period = "1y"
                else:
                    period = "5y"
                
                hist = ticker.history(period=period, interval=yf_interval)
            
            if hist.empty:
                return []
            
            # Convert to CandleData objects
            candles = []
            for timestamp, row in hist.tail(limit).iterrows():
                candle = CandleData(
                    timestamp=timestamp.to_pydatetime(),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row["Volume"]),
                    volume_usd=float(row["Volume"]) * float(row["Close"]),
                )
                candles.append(candle)
            
            return candles
            
        except Exception as e:
            logger.error(f"Failed to get candles for {symbol}: {e}")
            raise ValueError(f"Could not fetch candle data for '{symbol}': {e}")
    
    def get_company_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get company information and fundamentals.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with company information
        """
        try:
            normalized = self.normalize_symbol(symbol)
            ticker = self._get_yf_ticker(normalized)
            info = ticker.info
            
            return {
                "symbol": normalized,
                "name": info.get("longName", info.get("shortName", normalized)),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "country": info.get("country"),
                "currency": info.get("currency"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "dividend_yield": info.get("dividendYield"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
                "avg_volume": info.get("averageVolume"),
                "beta": info.get("beta"),
                "description": info.get("longBusinessSummary", "")[:500],
                "website": info.get("website"),
                "employees": info.get("fullTimeEmployees"),
                "provider": self.name,
            }
            
        except Exception as e:
            logger.error(f"Failed to get company info for {symbol}: {e}")
            return {"symbol": symbol, "error": str(e)}
    
    def health_check(self) -> bool:
        """
        Check if Yahoo Finance API is accessible.
        
        Returns:
            True if API is reachable and responding
        """
        try:
            # Try to get a common stock as health check
            ticker = yf.Ticker("AAPL")
            hist = ticker.history(period="1d")
            return not hist.empty
        except Exception:
            return False
    
    @staticmethod
    def is_stock_symbol(symbol: str) -> bool:
        """
        Check if a symbol appears to be a stock rather than crypto.
        
        Args:
            symbol: Symbol to check
            
        Returns:
            True if symbol looks like a stock ticker
        """
        symbol_upper = symbol.upper().strip()
        
        # Check against known stocks
        if symbol_upper in POPULAR_STOCKS:
            return True
        
        # Check against known stock names
        if symbol_upper in STOCK_NAME_TO_SYMBOL:
            return True
        
        # Check for exchange suffixes (.DE, .L, .PA, etc.)
        if "." in symbol and any(
            symbol.upper().endswith(suffix) 
            for suffix in [".DE", ".L", ".PA", ".MI", ".SW", ".AS", ".BR", ".HK", ".T"]
        ):
            return True
        
        # Check for index symbols (^GSPC, ^DJI, etc.)
        if symbol.startswith("^"):
            return True
        
        return False
