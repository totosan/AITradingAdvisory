# Copilot Instructions - Crypto Analysis Platform

## Architecture Overview

This is a **MagenticOne multi-agent system** being migrated from console to web application. The platform uses AutoGen's orchestrator pattern where specialized AI agents collaborate to analyze crypto markets.

### Current Architecture (Dual-Mode)

```
Console Mode (src/main.py)     Web Mode (backend/ - in progress)
         │                              │
         ▼                              ▼
┌─────────────────┐           ┌─────────────────┐
│ Rich Console UI │           │ FastAPI + WS    │
└────────┬────────┘           └────────┬────────┘
         │                              │
         └──────────┬───────────────────┘
                    ▼
         ┌─────────────────────┐
         │ MagenticOneGroupChat │
         │   6 Specialized      │
         │      Agents          │
         └──────────┬──────────┘
                    ▼
         ┌─────────────────────┐
         │  crypto_tools.py    │ ← CoinGecko API (cached via src/cache.py)
         │  exchange_tools.py  │ ← Bitget Exchange (real-time)
         └─────────────────────┘
```

### Key Components

- **Agents** (defined in `src/main.py`):
  - `CryptoMarketAnalyst` - Prices, market data (crypto_tools + exchange_tools)
  - `TechnicalAnalyst` - Charts, indicators, signals
  - `ChartingAgent` - TradingView charts, dashboards
  - `CryptoAnalysisCoder` - Python scripts, custom indicators
  - `ReportWriter` - Professional Markdown reports
  - `Executor` (CodeExecutorAgent) - Isolated code execution

- **Backend API** (in `backend/app/`):
  - FastAPI with WebSocket for real-time streaming
  - Health endpoints: `/api/v1/health`, `/api/v1/health/ready`
  - API spec: `docs/api/openapi.yaml`

## Migration Context

**IMPORTANT**: This codebase is undergoing console→web migration. Track progress in:
- `docs/migration/PROGRESS.md` - Current status and session logs
- `docs/migration/CHECKLIST.md` - Task checklist
- `docs/migration/PHASE_*.md` - Detailed implementation guides

Current phase: **Phase 1 (Backend API)** - WebSocket and Agent Service pending.

## Function Calling Pattern

**Critical**: Custom function calling for Ollama models in `src/ollama_client.py`:

```python
# Use Annotated for LLM parameter descriptions
def get_crypto_price(
    symbol: Annotated[str, "The cryptocurrency symbol (e.g., 'bitcoin', 'ethereum')"]
) -> str:  # Always return str (JSON for structured data)
```

When adding new tools:
1. Use `Annotated[type, "description"]` for parameters
2. Add to agent's `tools=[]` list in `src/main.py`
3. Return `str` (use `json.dumps()` for structured data)
4. Always handle errors: `return f"Error: {str(e)}"`

## Development Workflow

```bash
# Console mode (existing)
source .venv/bin/activate && python -m src.main

# Backend API (new - Phase 1)
cd backend && uvicorn app.main:app --reload

# Run tests (23 tests for crypto_tools)
pytest tests/ -v

# Full Docker stack
make setup && make start && make run
```

### Environment Setup
```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Code Conventions

### API Rate Limiting
Use `src/cache.py` TTLCache for CoinGecko (50 calls/min limit):
```python
from cache import cached, TTLCache
@cached(ttl_seconds=TTLCache.TTL_PRICE)  # 30s for prices
def get_crypto_price(symbol: str) -> str: ...
```

### Pydantic Models (Backend)
- Requests: `backend/app/models/requests.py`
- Responses: `backend/app/models/responses.py`  
- WebSocket Events: `backend/app/models/events.py`

### Output Files
All go to `outputs/` - use `Path(config.output_dir)`, not hardcoded paths.

## Key Files Reference

| Purpose | File |
|---------|------|
| Console entry | `src/main.py` |
| Backend entry | `backend/app/main.py` |
| LLM client | `src/ollama_client.py` |
| Crypto data | `src/crypto_tools.py` |
| API cache | `src/cache.py` |
| Tests | `tests/test_crypto_tools.py` |
| API spec | `docs/api/openapi.yaml` |
| Migration status | `docs/migration/PROGRESS.md` |

## Common Pitfalls

1. **CoinGecko rate limits**: Use TTLCache decorators, not raw API calls
2. **Function calling fails**: Check model in `ollama_client.py` capabilities
3. **Coin not found**: Use CoinGecko IDs (`bitcoin`) not tickers (`BTC`)
4. **Tests fail**: Recreate venv with `uv venv && uv pip install -e ".[dev]"`
5. **Backend imports fail**: Install `fastapi uvicorn httpx pydantic-settings`
