"""
Test configuration and fixtures for MagenticOne.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ============================================================================
# Mock API Responses
# ============================================================================

@pytest.fixture
def mock_coingecko_price_response():
    """Mock CoinGecko simple price API response."""
    return {
        "bitcoin": {
            "usd": 95000.00,
            "usd_24h_change": 2.5,
            "usd_24h_vol": 50000000000,
            "usd_market_cap": 1900000000000
        },
        "ethereum": {
            "usd": 3500.00,
            "usd_24h_change": -1.2,
            "usd_24h_vol": 20000000000,
            "usd_market_cap": 420000000000
        }
    }


@pytest.fixture
def mock_coingecko_market_data():
    """Mock CoinGecko market data response."""
    return {
        "id": "bitcoin",
        "symbol": "btc",
        "name": "Bitcoin",
        "market_data": {
            "current_price": {"usd": 95000},
            "market_cap": {"usd": 1900000000000},
            "total_volume": {"usd": 50000000000},
            "high_24h": {"usd": 96000},
            "low_24h": {"usd": 93000},
            "price_change_percentage_24h": 2.5,
            "price_change_percentage_7d": 5.0,
            "price_change_percentage_30d": 15.0,
            "circulating_supply": 19500000,
            "total_supply": 21000000,
            "ath": {"usd": 100000},
            "ath_date": {"usd": "2024-11-15T00:00:00.000Z"},
        }
    }


@pytest.fixture
def mock_coingecko_historical_data():
    """Mock CoinGecko historical price data (30 days)."""
    import time
    base_time = int(time.time() * 1000)
    day_ms = 86400000
    
    # Generate 30 days of price data
    prices = []
    base_price = 90000
    for i in range(30):
        timestamp = base_time - (30 - i) * day_ms
        price = base_price + (i * 200) + (i % 3 * 500)
        prices.append([timestamp, price])
    
    return {
        "prices": prices,
        "market_caps": [[p[0], p[1] * 20000000] for p in prices],
        "total_volumes": [[p[0], p[1] * 500000] for p in prices]
    }


@pytest.fixture
def mock_ohlcv_data():
    """Mock OHLCV candlestick data for charting."""
    import time
    base_time = int(time.time() * 1000)
    hour_ms = 3600000
    
    candles = []
    base_price = 95000
    for i in range(100):
        timestamp = base_time - (100 - i) * hour_ms
        open_price = base_price + (i * 10) + (i % 5 * 50)
        high = open_price + 200
        low = open_price - 150
        close = open_price + (50 if i % 2 == 0 else -30)
        volume = 1000000 + (i * 10000)
        candles.append({
            "timestamp": timestamp,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume
        })
    
    return candles


# ============================================================================
# Mock HTTP Responses
# ============================================================================

@pytest.fixture
def mock_requests_get(monkeypatch):
    """Mock requests.get for synchronous API calls."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    
    mock_get = MagicMock(return_value=mock_response)
    monkeypatch.setattr("requests.get", mock_get)
    
    return mock_get, mock_response


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp ClientSession for async API calls."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={})
    
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    return mock_session, mock_response


# ============================================================================
# Test Configuration
# ============================================================================

@pytest.fixture
def test_config():
    """Test configuration dictionary."""
    return {
        "llm_provider": "ollama",
        "ollama_base_url": "http://localhost:11434",
        "ollama_model": "gpt-oss:20b",
        "max_turns": 5,  # Lower for tests
        "output_dir": "/tmp/test_outputs"
    }


@pytest.fixture
def output_dir(tmp_path):
    """Create a temporary output directory."""
    output = tmp_path / "outputs"
    output.mkdir()
    (output / "charts").mkdir()
    (output / "reports").mkdir()
    return output


# ============================================================================
# Async Test Support
# ============================================================================

@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
