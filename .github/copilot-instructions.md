# Copilot Instructions - Crypto Analysis Platform

## Architecture Overview

This is a **MagenticOne multi-agent system** migrated from console to web application. The platform uses AutoGen's orchestrator pattern where specialized AI agents collaborate to analyze crypto markets.

### Current Architecture (Web Mode Active)

```
Console Mode (src/main.py)     Web Mode (backend/ + frontend/)
         │                              │
         ▼                              ▼
┌─────────────────┐           ┌─────────────────┐
│ Rich Console UI │           │ FastAPI + WS    │ ← Port 8500
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
  - Config reads from project root `.env` file
  - API spec: `docs/api/openapi.yaml`

- **Frontend** (in `frontend/`):
  - React + Vite + TypeScript
  - 4-panel layout: Chat, Status, Results, Charts
  - Zustand for state, React Query for data fetching
  - WebSocket client with reconnection logic

## Migration Status

**Phases 0-3 COMPLETE** ✅ | **Phases 4-5 IN PROGRESS** 🔄

Track progress in:
- `docs/migration/PROGRESS.md` - Current status and session logs
- `docs/migration/CHECKLIST.md` - Task checklist
- `docs/migration/PHASE_*.md` - Detailed implementation guides

Current focus: **Phase 4 (Secrets)** and **Phase 5 (Containers)**

### Verified Working (2025-12-01):
- ✅ Backend API on port 8500
- ✅ Azure OpenAI integration configured
- ✅ WebSocket streaming with ping/pong
- ✅ Frontend builds (0 TypeScript errors)
- ✅ 36/36 unit tests passing

## Function Calling Pattern

When adding new tools:
1. Use `Annotated[type, "description"]` for parameters
2. Add to agent's `tools=[]` list in `src/main.py`
3. Return `str` (use `json.dumps()` for structured data)
4. Always handle errors: `return f"Error: {str(e)}"`

```python
# Example tool function
def get_crypto_price(
    symbol: Annotated[str, "The cryptocurrency symbol (e.g., 'bitcoin', 'ethereum')"]
) -> str:  # Always return str (JSON for structured data)
```

## Development Workflow

```bash
# Console mode (existing)
source .venv/bin/activate && python -m src.main

# Backend API (port 8500 to avoid VS Code conflicts)
cd backend && ../.venv/bin/python3 -m uvicorn app.main:app --port 8500 --reload

# Frontend dev server (port 5173)
cd frontend && npm run dev

# Run tests
source .venv/bin/activate && pytest tests/ -v

# Full Docker stack (after Phase 5)
make setup && make start && make run
```

### Environment Setup
```bash
# Create and activate venv
python3 -m venv .venv && source .venv/bin/activate

# Install backend dependencies
pip install fastapi uvicorn httpx pydantic-settings websockets python-multipart

# Frontend setup
cd frontend && npm install
```

### Environment Variables
All config in project root `.env` file (see `.env.example`):
- `LLM_PROVIDER` - "azure" or "ollama"
- `AZURE_OPENAI_*` - Azure OpenAI credentials
- `BITGET_*` - Exchange API credentials
- `EXCHANGE_DEFAULT_PROVIDER` - "coingecko" or "bitget"

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
| Frontend entry | `frontend/src/App.tsx` |
| Crypto data | `src/crypto_tools.py` |
| API cache | `src/cache.py` |
| Tests | `tests/test_crypto_tools.py` |
| API spec | `docs/api/openapi.yaml` |
| Migration status | `docs/migration/PROGRESS.md` |

## Frontend Architecture

```
frontend/src/
├── components/
│   ├── features/      # ChatPanel, StatusPanel, ResultsPanel, ChartPanel
│   ├── layout/        # Header, MainLayout, PanelContainer
│   └── ui/            # Button, Card, Input (shadcn/ui style)
├── hooks/             # useWebSocket, useChat
├── services/          # WebSocket service (ws://localhost:8500)
├── stores/            # Zustand stores (chat, status, charts)
└── types/             # TypeScript interfaces matching backend models
```

## Common Pitfalls

1. **CoinGecko rate limits**: Use TTLCache decorators, not raw API calls
2. **Coin not found**: Use CoinGecko IDs (`bitcoin`) not tickers (`BTC`)
3. **Tests fail**: Recreate venv with `uv venv && uv pip install -e ".[dev]"`
4. **Backend imports fail**: Install `fastapi uvicorn httpx pydantic-settings`
