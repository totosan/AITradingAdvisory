"""
Crypto Analysis Tools for AgenticTrades

This module provides tools for cryptocurrency analysis including:
- Real-time price fetching (via exchange providers)
- Historical data retrieval
- Technical indicator calculations
- Chart generation

Note: This module maintains backward compatibility with the original CoinGecko-based
implementation while also supporting the new exchange provider system. For advanced
features (orderbook, futures, account data), use exchange_tools.py instead.
"""
import requests
import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple, Annotated
from datetime import datetime, timedelta
import json

# Import caching for rate limit protection
try:
    from .cache import TTLCache, api_cache
except ImportError:
    from cache import TTLCache, api_cache

# Import exchange providers for enhanced functionality
try:
    from .exchange_providers import (
        ExchangeManager,
        ProviderType,
        CoinGeckoProvider,
        BitgetProvider,
    )
    EXCHANGE_PROVIDERS_AVAILABLE = True
except ImportError:
    try:
        from exchange_providers import (
            ExchangeManager,
            ProviderType,
            CoinGeckoProvider,
            BitgetProvider,
        )
        EXCHANGE_PROVIDERS_AVAILABLE = True
    except ImportError:
        EXCHANGE_PROVIDERS_AVAILABLE = False


class CryptoDataFetcher:
    """
    Fetch cryptocurrency data from public APIs.
    
    This class maintains the original CoinGecko-based implementation for
    backward compatibility. For advanced exchange features, use the
    ExchangeManager from exchange_providers module.
    """
    
    def __init__(self, use_providers: bool = False):
        """
        Initialize the data fetcher.
        
        Args:
            use_providers: If True and available, use ExchangeManager for data.
                          If False, use direct CoinGecko API calls (original behavior).
        """
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        self._use_providers = use_providers and EXCHANGE_PROVIDERS_AVAILABLE
        self._manager: Optional[ExchangeManager] = None
        
        if self._use_providers:
            self._init_providers()
    
    def _init_providers(self) -> None:
        """Initialize exchange providers."""
        self._manager = ExchangeManager()
        self._manager.register_provider(ProviderType.COINGECKO, CoinGeckoProvider())
        
        # Try to add Bitget if configured
        try:
            bitget = BitgetProvider.from_env()
            self._manager.register_provider(ProviderType.BITGET, bitget)
            if bitget.is_authenticated:
                self._manager.set_default_provider(ProviderType.BITGET)
        except Exception:
            pass
        
    def get_crypto_price(
        self,
        symbol: Annotated[str, "The cryptocurrency symbol (e.g., 'bitcoin', 'ethereum', 'solana')"],
    ) -> str:
        """
        Get current price and basic market data for a cryptocurrency.
        
        Args:
            symbol: Cryptocurrency symbol or ID (e.g., 'bitcoin', 'ethereum')
            
        Returns:
            JSON string with price, market cap, volume, and price changes
        """
        # Check cache first (30 second TTL for price data)
        cache_key = f"price:{symbol.lower()}"
        cached = api_cache.get(cache_key, TTLCache.TTL_PRICE)
        if cached is not None:
            return cached
        
        try:
            url = f"{self.coingecko_base}/simple/price"
            params = {
                'ids': symbol.lower(),
                'vs_currencies': 'usd',
                'include_market_cap': 'true',
                'include_24hr_vol': 'true',
                'include_24hr_change': 'true',
                'include_last_updated_at': 'true'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return f"Error: Cryptocurrency '{symbol}' not found. Try common names like 'bitcoin', 'ethereum', 'solana'."
            
            result = json.dumps(data, indent=2)
            api_cache.set(cache_key, result, TTLCache.TTL_PRICE)
            return result
            
        except Exception as e:
            return f"Error fetching price data: {str(e)}"
    
    def get_historical_data(
        self,
        symbol: Annotated[str, "The cryptocurrency symbol (e.g., 'bitcoin', 'ethereum')"],
        days: Annotated[int, "Number of days of historical data (1-365)"] = 30,
    ) -> str:
        """
        Get historical price data for a cryptocurrency.
        
        Args:
            symbol: Cryptocurrency symbol or ID
            days: Number of days of historical data (1-365)
            
        Returns:
            JSON string with historical prices, market caps, and volumes
        """
        # Check cache first (5 minute TTL for historical data)
        cache_key = f"historical:{symbol.lower()}:{days}"
        cached = api_cache.get(cache_key, TTLCache.TTL_HISTORICAL)
        if cached is not None:
            return cached
        
        try:
            url = f"{self.coingecko_base}/coins/{symbol.lower()}/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': min(days, 365),
                'interval': 'daily' if days > 1 else 'hourly'
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Convert to more readable format
            df_prices = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
            df_prices['date'] = pd.to_datetime(df_prices['timestamp'], unit='ms')
            
            result = {
                'symbol': symbol,
                'days': days,
                'data_points': len(df_prices),
                'latest_price': df_prices['price'].iloc[-1],
                'oldest_price': df_prices['price'].iloc[0],
                'price_change_pct': ((df_prices['price'].iloc[-1] - df_prices['price'].iloc[0]) / df_prices['price'].iloc[0] * 100),
                'highest_price': df_prices['price'].max(),
                'lowest_price': df_prices['price'].min(),
                'prices': df_prices[['date', 'price']].tail(10).to_dict('records')
            }
            
            result_str = json.dumps(result, indent=2, default=str)
            api_cache.set(cache_key, result_str, TTLCache.TTL_HISTORICAL)
            return result_str
            
        except Exception as e:
            return f"Error fetching historical data: {str(e)}"
    
    def get_market_info(
        self,
        symbol: Annotated[str, "The cryptocurrency symbol (e.g., 'bitcoin', 'ethereum')"],
    ) -> str:
        """
        Get detailed market information for a cryptocurrency.
        
        Args:
            symbol: Cryptocurrency symbol or ID
            
        Returns:
            JSON string with detailed market data
        """
        # Check cache first (2 minute TTL for market info)
        cache_key = f"market_info:{symbol.lower()}"
        cached = api_cache.get(cache_key, TTLCache.TTL_MARKET_INFO)
        if cached is not None:
            return cached
        
        try:
            url = f"{self.coingecko_base}/coins/{symbol.lower()}"
            params = {
                'localization': 'false',
                'tickers': 'false',
                'community_data': 'true',
                'developer_data': 'false'
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            market_data = data.get('market_data', {})
            
            result = {
                'name': data.get('name'),
                'symbol': data.get('symbol', '').upper(),
                'current_price_usd': market_data.get('current_price', {}).get('usd'),
                'market_cap_usd': market_data.get('market_cap', {}).get('usd'),
                'market_cap_rank': market_data.get('market_cap_rank'),
                'total_volume_usd': market_data.get('total_volume', {}).get('usd'),
                'price_change_24h': market_data.get('price_change_percentage_24h'),
                'price_change_7d': market_data.get('price_change_percentage_7d'),
                'price_change_30d': market_data.get('price_change_percentage_30d'),
                'ath_usd': market_data.get('ath', {}).get('usd'),
                'ath_change_percentage': market_data.get('ath_change_percentage', {}).get('usd'),
                'atl_usd': market_data.get('atl', {}).get('usd'),
                'circulating_supply': market_data.get('circulating_supply'),
                'total_supply': market_data.get('total_supply'),
                'max_supply': market_data.get('max_supply'),
            }
            
            result_str = json.dumps(result, indent=2)
            api_cache.set(cache_key, result_str, TTLCache.TTL_MARKET_INFO)
            return result_str
            
        except Exception as e:
            return f"Error fetching market info: {str(e)}"


class TechnicalIndicators:
    """Calculate technical analysis indicators."""
    
    @staticmethod
    def calculate_sma(
        prices: List[float],
        period: int = 20
    ) -> List[float]:
        """Calculate Simple Moving Average."""
        if len(prices) < period:
            return []
        
        sma = []
        for i in range(len(prices) - period + 1):
            sma.append(sum(prices[i:i+period]) / period)
        
        return sma
    
    @staticmethod
    def calculate_ema(
        prices: List[float],
        period: int = 20
    ) -> List[float]:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return []
        
        multiplier = 2 / (period + 1)
        ema = [sum(prices[:period]) / period]  # First EMA is SMA
        
        for price in prices[period:]:
            ema.append((price - ema[-1]) * multiplier + ema[-1])
        
        return ema
    
    @staticmethod
    def calculate_rsi(
        prices: List[float],
        period: int = 14
    ) -> List[float]:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return []
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        rsi = []
        for i in range(period, len(gains)):
            if avg_loss == 0:
                rsi.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi.append(100 - (100 / (1 + rs)))
            
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        return rsi
    
    @staticmethod
    def calculate_macd(
        prices: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[List[float], List[float], List[float]]:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        if len(prices) < slow_period:
            return [], [], []
        
        ema_fast = TechnicalIndicators.calculate_ema(prices, fast_period)
        ema_slow = TechnicalIndicators.calculate_ema(prices, slow_period)
        
        # Align the EMAs
        offset = len(ema_fast) - len(ema_slow)
        macd_line = [ema_fast[i + offset] - ema_slow[i] for i in range(len(ema_slow))]
        
        # Calculate signal line
        signal_line = TechnicalIndicators.calculate_ema(macd_line, signal_period)
        
        # Calculate histogram
        histogram_offset = len(macd_line) - len(signal_line)
        histogram = [macd_line[i + histogram_offset] - signal_line[i] for i in range(len(signal_line))]
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def calculate_bollinger_bands(
        prices: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[List[float], List[float], List[float]]:
        """
        Calculate Bollinger Bands.
        
        Returns:
            Tuple of (upper_band, middle_band, lower_band)
        """
        if len(prices) < period:
            return [], [], []
        
        middle_band = TechnicalIndicators.calculate_sma(prices, period)
        
        upper_band = []
        lower_band = []
        
        for i in range(len(prices) - period + 1):
            window = prices[i:i+period]
            std = np.std(window)
            upper_band.append(middle_band[i] + (std_dev * std))
            lower_band.append(middle_band[i] - (std_dev * std))
        
        return upper_band, middle_band, lower_band
    
    @staticmethod
    def analyze_technical_indicators(
        symbol: Annotated[str, "The cryptocurrency symbol"],
        prices: Annotated[List[float], "List of historical prices"],
    ) -> str:
        """
        Perform comprehensive technical analysis on price data.
        
        Args:
            symbol: Cryptocurrency symbol
            prices: List of historical prices
            
        Returns:
            JSON string with technical analysis results
        """
        if len(prices) < 50:
            return "Error: Need at least 50 data points for reliable technical analysis"
        
        try:
            # Calculate indicators
            current_price = prices[-1]
            sma_20 = TechnicalIndicators.calculate_sma(prices, 20)
            sma_50 = TechnicalIndicators.calculate_sma(prices, 50)
            ema_12 = TechnicalIndicators.calculate_ema(prices, 12)
            ema_26 = TechnicalIndicators.calculate_ema(prices, 26)
            rsi = TechnicalIndicators.calculate_rsi(prices, 14)
            macd_line, signal_line, histogram = TechnicalIndicators.calculate_macd(prices)
            upper_bb, middle_bb, lower_bb = TechnicalIndicators.calculate_bollinger_bands(prices, 20)
            
            # Determine signals
            signals = []
            
            # RSI signals
            if rsi and rsi[-1] < 30:
                signals.append("RSI indicates OVERSOLD condition (potential buy signal)")
            elif rsi and rsi[-1] > 70:
                signals.append("RSI indicates OVERBOUGHT condition (potential sell signal)")
            
            # MACD signals
            if macd_line and signal_line and len(histogram) > 1:
                if histogram[-1] > 0 and histogram[-2] <= 0:
                    signals.append("MACD bullish crossover (buy signal)")
                elif histogram[-1] < 0 and histogram[-2] >= 0:
                    signals.append("MACD bearish crossover (sell signal)")
            
            # Bollinger Bands signals
            if upper_bb and lower_bb:
                bb_position = (current_price - lower_bb[-1]) / (upper_bb[-1] - lower_bb[-1]) * 100
                if bb_position < 20:
                    signals.append("Price near lower Bollinger Band (potential oversold)")
                elif bb_position > 80:
                    signals.append("Price near upper Bollinger Band (potential overbought)")
            
            # Moving average trends
            if sma_20 and sma_50:
                if sma_20[-1] > sma_50[-1]:
                    signals.append("SMA20 above SMA50 (bullish trend)")
                else:
                    signals.append("SMA20 below SMA50 (bearish trend)")
            
            result = {
                'symbol': symbol,
                'current_price': current_price,
                'analysis_timestamp': datetime.now().isoformat(),
                'indicators': {
                    'sma_20': sma_20[-1] if sma_20 else None,
                    'sma_50': sma_50[-1] if sma_50 else None,
                    'ema_12': ema_12[-1] if ema_12 else None,
                    'ema_26': ema_26[-1] if ema_26 else None,
                    'rsi_14': rsi[-1] if rsi else None,
                    'macd': macd_line[-1] if macd_line else None,
                    'macd_signal': signal_line[-1] if signal_line else None,
                    'macd_histogram': histogram[-1] if histogram else None,
                    'bollinger_upper': upper_bb[-1] if upper_bb else None,
                    'bollinger_middle': middle_bb[-1] if middle_bb else None,
                    'bollinger_lower': lower_bb[-1] if lower_bb else None,
                },
                'signals': signals,
                'overall_sentiment': 'Bullish' if len([s for s in signals if 'buy' in s.lower() or 'bullish' in s.lower()]) > len([s for s in signals if 'sell' in s.lower() or 'bearish' in s.lower()]) else 'Bearish'
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return f"Error calculating technical indicators: {str(e)}"


# Create singleton instances for tools
crypto_data_fetcher = CryptoDataFetcher()
tech_indicators = TechnicalIndicators()

# Export tool functions for agent use
def get_crypto_price(symbol: str) -> str:
    """Get current cryptocurrency price and market data."""
    return crypto_data_fetcher.get_crypto_price(symbol)

def get_historical_data(symbol: str, days: int = 30) -> str:
    """Get historical price data for technical analysis."""
    return crypto_data_fetcher.get_historical_data(symbol, days)

def get_market_info(symbol: str) -> str:
    """Get detailed market information and statistics."""
    return crypto_data_fetcher.get_market_info(symbol)

def analyze_technical_indicators(symbol: str, prices: List[float]) -> str:
    """Perform comprehensive technical analysis."""
    return tech_indicators.analyze_technical_indicators(symbol, prices)
