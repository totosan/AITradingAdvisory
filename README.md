# 🪙 Crypto Analysis Platform

Multi-agent cryptocurrency research workstation with FastAPI backend, React/Vite frontend, and TradingView-style visualization. The migration from console to web (Phases 0‑5) is complete—this repo now reflects the production-ready stack.

---

## 🎯 Key Capabilities
- 🤖 Specialized agent team for market data, indicators, charting, coding, reporting, and sandboxed execution
- 📈 Technical analysis toolkit (RSI, MACD, Bollinger Bands, EMAs) with caching + rate-limit protection
- 🖥️ Web experience with four-panel layout (Chat, Status, Results, Charts) and live WebSocket streaming
- 💾 Persistent artifacts saved under `outputs/` (charts, dashboards, alerts, code execution)
- 🔌 Data providers abstracted through CoinGecko + Bitget adapters

---

## 🚀 Quick Start (Docker)
1. Copy the environment template and fill credentials:
   ```bash
   cp .env.example .env
   ```
2. From your **host terminal** (outside the devcontainer):
   ```bash
   make dev
   ```
3. Open the forwarded ports:
   - Frontend → http://localhost:5173
   - API Docs → http://localhost:8500/docs

Stop everything with `Ctrl+C` or `make stop`.

---

## 💻 Local Development (no Docker)
Recommended inside the VS Code devcontainer:

```bash
make dev-local        # Backend + frontend with hot reload
make dev-backend      # FastAPI only (uses .venv)
make dev-frontend     # React dev server only
```

Manual start:
```bash
# Backend
source .venv/bin/activate
python -m backend.app.main

# Frontend
cd frontend && npm run dev
```

---

## 🧪 Verification & Tests
- Health check: `curl http://localhost:8500/api/v1/health`
- WebSocket smoke test: `python backend/test_websocket.py`
- Unit tests: `source .venv/bin/activate && pytest tests -v`
- Full-stack test (agents + streaming): `python test_live_agent.py`

---

## ⚙️ Configuration

### 1. Base Environment
```bash
cp .env.example .env
```
Fill in one of the LLM providers:

#### Azure OpenAI
```bash
LLM_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

#### Ollama (local)
```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2:latest
```

### 2. Optional Exchange Keys
```bash
BITGET_API_KEY=...
BITGET_API_SECRET=...
BITGET_PASSPHRASE=...
```

---

## 🧭 Project Layout
```
MagenticOne/
├── backend/            # FastAPI app, routers, services, models
├── frontend/           # React + Vite client
├── src/                # Original console agents + shared tooling
├── tests/              # Pytest suite (unit + integration)
├── outputs/            # Charts, dashboards, code execution artifacts
├── docs/migration/     # Progress + checklist (archive holds phase docs)
├── Dockerfile, docker-compose.*
├── Makefile
└── pyproject.toml, uv.lock
```

---

## 🛠️ Make Commands
| Command | Description |
|---------|-------------|
| `make dev` | Backend + frontend via Docker (recommended) |
| `make dev-local` | Run both services locally with hot reload |
| `make dev-backend` / `make dev-frontend` | Start individual stacks |
| `make prod` | Production-grade docker-compose stack |
| `make stop` | Stop all running services |
| `make logs` | Tail container logs |
| `make status` | Container health summary |

Run `make help` to see every available target.

---

## 💬 Using the Assistant
- Ask for prices, indicator breakdowns, or strategy ideas: `Analyze BTCUSDT with MACD + RSI`
- Chain questions—the MagenticOne group chat remembers context.
- Charts appear automatically in the Charts panel whenever agents emit `chart_file` outputs.
- CLI chat commands: `/clear`, `/history`, `/single` (toggle one-shot mode)

Example prompts:
```
Generate a multi-timeframe dashboard for ETH with support/resistance
Compare SOL vs AVAX performance and highlight divergences
Create a TradingView chart for SUI with RSI and volume
```

---

## 📡 Data & Symbols
| Provider | Format | Example |
|----------|--------|---------|
| CoinGecko | lowercase asset id | `bitcoin`, `solana`, `sui` |
| Bitget | pair symbol | `BTCUSDT`, `ETHUSDT`, `SUIUSDT` |

Caching via `src/cache.py` shields CoinGecko from rate limits (30‑second TTL for price queries).

---

## ⚠️ Disclaimer
Educational and research purposes only. This is **not** financial advice; trading crypto involves substantial risk.

---

## 🧱 Built With
- [AutoGen / MagenticOne](https://github.com/microsoft/autogen)
- [FastAPI](https://fastapi.tiangolo.com) + [Uvicorn](https://www.uvicorn.org)
- [React](https://react.dev) + [Vite](https://vitejs.dev)
- [CoinGecko API](https://www.coingecko.com) & [Bitget API](https://www.bitget.com)
- [Azure OpenAI](https://azure.microsoft.com/products/ai-services/openai-service) or [Ollama](https://ollama.ai) for LLMs
