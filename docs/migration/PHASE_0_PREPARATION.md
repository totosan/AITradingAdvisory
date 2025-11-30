# Phase 0: Pre-Migration Preparation

## Overview

Essential preparation tasks before starting the web application migration. These tasks reduce risk and establish a solid foundation.

---

## 0.1 Test Coverage Baseline

Before refactoring, ensure critical functionality has tests to prevent regressions.

### Priority Test Files

```bash
# Create test directory
mkdir -p tests
touch tests/__init__.py
touch tests/conftest.py
touch tests/test_crypto_tools.py
touch tests/test_exchange_tools.py
touch tests/test_ollama_client.py
```

### Critical Functions to Test

| Module | Function | Priority |
|--------|----------|----------|
| `crypto_tools.py` | `get_crypto_price()` | High |
| `crypto_tools.py` | `get_historical_data()` | High |
| `crypto_tools.py` | `get_market_info()` | Medium |
| `exchange_tools.py` | `get_realtime_price()` | High |
| `exchange_tools.py` | `get_ohlcv_data()` | High |
| `ollama_client.py` | `OllamaChatCompletionClient.create()` | High |
| `indicator_registry.py` | `save_custom_indicator()` | Medium |
| `indicator_registry.py` | `get_custom_indicator()` | Medium |

### Test Configuration

```python
# tests/conftest.py
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

@pytest.fixture
def mock_coingecko_response():
    """Mock CoinGecko API response for testing."""
    return {
        "bitcoin": {
            "usd": 95000,
            "usd_24h_change": 2.5,
            "usd_24h_vol": 50000000000,
            "usd_market_cap": 1900000000000
        }
    }
```

---

## 0.2 API Contract Definition (OpenAPI)

Define the API contract before implementation to ensure frontend/backend alignment.

### Create OpenAPI Specification

```yaml
# docs/api/openapi.yaml
openapi: 3.0.3
info:
  title: MagenticOne Crypto Analysis API
  description: Multi-agent cryptocurrency analysis platform
  version: 1.0.0

servers:
  - url: http://localhost:8000/api/v1
    description: Development server

paths:
  /health:
    get:
      summary: Health check
      responses:
        '200':
          description: Healthy
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthResponse'

  /chat/message:
    post:
      summary: Send a chat message (triggers agent analysis)
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ChatMessage'
      responses:
        '200':
          description: Analysis started
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ChatResponse'

  /charts/generate:
    post:
      summary: Generate a chart
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ChartRequest'
      responses:
        '200':
          description: Chart generated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ChartResponse'

  /settings/exchange:
    post:
      summary: Save exchange credentials (encrypted)
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ExchangeCredentials'
      responses:
        '200':
          description: Credentials saved
    get:
      summary: Get exchange connection status
      responses:
        '200':
          description: Status retrieved

components:
  schemas:
    HealthResponse:
      type: object
      properties:
        status:
          type: string
          enum: [healthy, degraded, unhealthy]
        timestamp:
          type: string
          format: date-time

    ChatMessage:
      type: object
      required:
        - message
      properties:
        message:
          type: string
          minLength: 1
          maxLength: 5000
        conversation_id:
          type: string

    ChatResponse:
      type: object
      properties:
        conversation_id:
          type: string
        status:
          type: string

    ChartRequest:
      type: object
      required:
        - symbol
      properties:
        symbol:
          type: string
          example: BTCUSDT
        interval:
          type: string
          default: "1H"
        indicators:
          type: array
          items:
            type: string

    ChartResponse:
      type: object
      properties:
        chart_id:
          type: string
        url:
          type: string

    ExchangeCredentials:
      type: object
      required:
        - api_key
        - api_secret
        - passphrase
      properties:
        api_key:
          type: string
        api_secret:
          type: string
        passphrase:
          type: string
```

---

## 0.3 Caching Layer for API Rate Limits

CoinGecko free tier: ~50 calls/minute. Add caching to prevent hitting limits.

### Caching Strategy

| Data Type | Cache Duration | Reason |
|-----------|----------------|--------|
| Current price | 30 seconds | Near real-time needed |
| Historical data | 5 minutes | Doesn't change frequently |
| Market info | 2 minutes | Moderate update frequency |
| Exchange status | 1 minute | Connection check |

### Implementation Approach

```python
# src/cache.py (to be created)
from functools import lru_cache
from datetime import datetime, timedelta
import asyncio

class TTLCache:
    """Simple time-based cache for API responses."""
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
    
    def get(self, key: str, ttl_seconds: int = 60):
        """Get cached value if not expired."""
        if key in self._cache:
            if datetime.now() - self._timestamps[key] < timedelta(seconds=ttl_seconds):
                return self._cache[key]
        return None
    
    def set(self, key: str, value):
        """Cache a value with current timestamp."""
        self._cache[key] = value
        self._timestamps[key] = datetime.now()

# Global cache instance
api_cache = TTLCache()
```

---

## 0.4 Conversation Persistence Decision

**Decision: Start with in-memory, plan for SQLite**

### Phase 1 (MVP)
- In-memory conversation storage
- Conversations lost on restart
- Simple dictionary-based

### Phase 2 (Post-MVP)
- SQLite for persistence
- Async with `aiosqlite`
- Schema:

```sql
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT REFERENCES conversations(id),
    role TEXT NOT NULL,  -- 'user', 'assistant', 'agent'
    content TEXT NOT NULL,
    agent_name TEXT,     -- NULL for user messages
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE charts (
    id TEXT PRIMARY KEY,
    conversation_id TEXT REFERENCES conversations(id),
    file_path TEXT NOT NULL,
    symbol TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 0.5 Environment Variables Audit

Document all environment variables needed:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | No | `ollama` | LLM backend (ollama/azure) |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | No | `gpt-oss:20b` | Model to use |
| `AZURE_OPENAI_API_KEY` | If azure | - | Azure OpenAI key |
| `AZURE_OPENAI_ENDPOINT` | If azure | - | Azure endpoint |
| `BITGET_API_KEY` | No | - | Exchange API key |
| `BITGET_API_SECRET` | No | - | Exchange secret |
| `BITGET_PASSPHRASE` | No | - | Exchange passphrase |
| `MAX_TURNS` | No | `20` | Max agent turns |
| `CORS_ORIGINS` | No | `localhost:3000,5173` | Allowed origins |
| `OUTPUT_DIR` | No | `outputs` | Output directory |

---

## 0.6 Pre-Migration Checklist

- [ ] Create `tests/` directory structure
- [ ] Add pytest and pytest-asyncio to dependencies
- [ ] Write tests for `crypto_tools.py` critical functions
- [ ] Write tests for `exchange_tools.py` critical functions
- [ ] Create OpenAPI specification file
- [ ] Implement basic caching layer
- [ ] Document all environment variables
- [ ] Verify Ollama connectivity
- [ ] Verify CoinGecko API access
- [ ] Back up current working state (git tag)

---

## 0.7 Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing console app | High | Keep `src/main.py` working, add backend separately |
| CoinGecko rate limits | Medium | Add caching layer |
| WebSocket complexity | Medium | Start with simple implementation, enhance later |
| LLM response streaming | Medium | Thoroughly test stream adapter |
| Docker networking | Low | Use `host.docker.internal` for Ollama |

---

*Created: 2025-11-30*
*Status: PENDING*
