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

**Phases 0-5 COMPLETE** ✅ (web migration finished)

Track artifacts in:
- `docs/migration/PROGRESS.md` – Current status and session logs
- `docs/migration/CHECKLIST.md` – Active checklist
- `docs/migration/archive/PHASE_*.md` – Archived phase guides + quick starts

Canonical setup + onboarding now lives in `README.md`.

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

## Python Environment Management

**Always use UV** for Python environment and package management. UV is a fast Python package installer and resolver.

```bash
# Create virtual environment with UV
uv venv

# Activate the environment
source .venv/bin/activate

# Install all dependencies from pyproject.toml
uv pip install -e ".[dev]"

# Install specific packages
uv pip install <package-name>

# Sync dependencies from lock file
uv sync
```

> ⚠️ **Important**: Never use raw `pip` commands. Always use `uv pip` for package operations.

## Development Workflow

```bash
# Docker (recommended)
cp .env.example .env && make dev

# Local (devcontainer) hot reload
make dev-local           # backend + frontend
make dev-backend         # FastAPI only
make dev-frontend        # React only

# Tests
source .venv/bin/activate && pytest tests/ -v
python backend/test_websocket.py   # WS smoke test
python test_live_agent.py          # full stack sanity

# Console fallback (legacy mode)
source .venv/bin/activate && python -m src.main
```

### Environment Setup
```bash
# Create and activate venv with UV
uv venv && source .venv/bin/activate

# Install all project dependencies
uv pip install -e ".[dev]"

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
| Project overview + quick start | `README.md` |
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
4. **Backend imports fail**: Run `uv pip install -e ".[dev]"` to install all dependencies
5. **Never use raw pip**: Always use `uv pip` for package management
