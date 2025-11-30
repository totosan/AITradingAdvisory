"""
TTL Cache for API Rate Limiting

Implements a simple time-based cache to prevent hitting CoinGecko rate limits.
CoinGecko free tier: ~50 calls/minute

Cache durations:
- Current price: 30 seconds (near real-time needed)
- Historical data: 5 minutes (doesn't change frequently)
- Market info: 2 minutes (moderate update frequency)
- Exchange status: 1 minute (connection check)
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, TypeVar, Callable
from functools import wraps
import threading
import hashlib
import json

T = TypeVar('T')


class TTLCache:
    """
    Thread-safe Time-To-Live cache for API responses.
    
    Usage:
        cache = TTLCache()
        
        # Store a value
        cache.set("bitcoin_price", {"usd": 95000}, ttl_seconds=30)
        
        # Retrieve if not expired
        value = cache.get("bitcoin_price", ttl_seconds=30)
        if value is None:
            # Cache miss or expired, fetch from API
            value = fetch_from_api()
            cache.set("bitcoin_price", value, ttl_seconds=30)
    """
    
    # Default TTL values (in seconds)
    TTL_PRICE = 30          # Real-time price data
    TTL_HISTORICAL = 300    # Historical data (5 minutes)
    TTL_MARKET_INFO = 120   # Market information (2 minutes)
    TTL_EXCHANGE = 60       # Exchange status (1 minute)
    
    def __init__(self):
        """Initialize the cache."""
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, datetime] = {}
        self._lock = threading.RLock()
    
    def _make_key(self, *args, **kwargs) -> str:
        """Create a cache key from function arguments."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str, ttl_seconds: int = 60) -> Optional[Any]:
        """
        Get cached value if not expired.
        
        Args:
            key: Cache key
            ttl_seconds: Maximum age of cached value in seconds
            
        Returns:
            Cached value if present and not expired, None otherwise
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            timestamp = self._timestamps.get(key)
            if timestamp is None:
                return None
            
            age = datetime.now() - timestamp
            if age > timedelta(seconds=ttl_seconds):
                # Expired, remove from cache
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)
                return None
            
            return self._cache[key]
    
    def set(self, key: str, value: Any, ttl_seconds: int = 60) -> None:
        """
        Cache a value with current timestamp.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: TTL hint (not enforced on set, only on get)
        """
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = datetime.now()
    
    def delete(self, key: str) -> bool:
        """
        Remove a key from the cache.
        
        Args:
            key: Cache key to remove
            
        Returns:
            True if key was present, False otherwise
        """
        with self._lock:
            existed = key in self._cache
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)
            return existed
    
    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
    
    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache statistics
        """
        with self._lock:
            now = datetime.now()
            entries = []
            for key in self._cache:
                timestamp = self._timestamps.get(key)
                if timestamp:
                    age = (now - timestamp).total_seconds()
                    entries.append({"key": key[:16] + "...", "age_seconds": age})
            
            return {
                "total_entries": len(self._cache),
                "entries": entries[:10]  # First 10 only
            }


# Global cache instance
api_cache = TTLCache()


def cached(ttl_seconds: int = 60, cache_key_prefix: str = ""):
    """
    Decorator to cache function results.
    
    Args:
        ttl_seconds: Cache TTL in seconds
        cache_key_prefix: Prefix for cache key (optional)
        
    Usage:
        @cached(ttl_seconds=30, cache_key_prefix="price")
        def get_crypto_price(symbol: str) -> str:
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Generate cache key
            key_parts = [cache_key_prefix or func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_value = api_cache.get(cache_key, ttl_seconds)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = func(*args, **kwargs)
            api_cache.set(cache_key, result, ttl_seconds)
            return result
        
        return wrapper
    return decorator


def cached_async(ttl_seconds: int = 60, cache_key_prefix: str = ""):
    """
    Decorator to cache async function results.
    
    Args:
        ttl_seconds: Cache TTL in seconds
        cache_key_prefix: Prefix for cache key (optional)
        
    Usage:
        @cached_async(ttl_seconds=30, cache_key_prefix="price")
        async def get_crypto_price(symbol: str) -> str:
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Generate cache key
            key_parts = [cache_key_prefix or func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_value = api_cache.get(cache_key, ttl_seconds)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            api_cache.set(cache_key, result, ttl_seconds)
            return result
        
        return wrapper
    return decorator


# Convenience decorators for specific TTL values
def cache_price(func: Callable[..., T]) -> Callable[..., T]:
    """Cache for real-time price data (30 seconds)."""
    return cached(ttl_seconds=TTLCache.TTL_PRICE)(func)


def cache_historical(func: Callable[..., T]) -> Callable[..., T]:
    """Cache for historical data (5 minutes)."""
    return cached(ttl_seconds=TTLCache.TTL_HISTORICAL)(func)


def cache_market_info(func: Callable[..., T]) -> Callable[..., T]:
    """Cache for market info (2 minutes)."""
    return cached(ttl_seconds=TTLCache.TTL_MARKET_INFO)(func)
