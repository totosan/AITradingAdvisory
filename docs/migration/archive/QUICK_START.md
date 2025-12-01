# Quick Start Guide - After Phase 3

## Current State

✅ **Phase 0**: Tests, caching, API spec  
✅ **Phase 1**: Backend API with all REST endpoints  
✅ **Phase 2**: React frontend with 4-panel layout  
✅ **Phase 3**: WebSocket + real-time agent streaming  
⏳ **Phase 4**: Secret management (next)  
⏳ **Phase 5**: Docker containerization ✅ **COMPLETE**

---

## 🐳 Starting the System (Docker)

From your **host terminal**:

```bash
cd /path/to/MagenticOne
make dev
```

**What you'll see:**
```
🔧 Starting development mode (Docker)...
[+] Building ...
 ✔ Container magentic-backend-dev    Started
 ✔ Container magentic-frontend-dev   Started
magentic-backend-dev   | 🚀 Starting MagenticOne API
magentic-backend-dev   |    Provider: azure
magentic-backend-dev   |    Model: gpt-4o
magentic-backend-dev   | INFO:     Uvicorn running on http://0.0.0.0:8500
```

**Access:**
- 🌐 Frontend: http://localhost:5173
- 📚 API Docs: http://localhost:8500/docs

Press `Ctrl+C` to stop.

---

## 🖥️ Local Mode (for devcontainers)

If you're inside a devcontainer or prefer local development:

```bash
make dev-local
```

Or run services separately:

```bash
# Terminal 1: Backend
make dev-backend

# Terminal 2: Frontend  
make dev-frontend
```

---

## Quick Tests

### Backend Health
```bash
curl http://localhost:8500/api/v1/health
curl http://localhost:8500/ws/status
```

### WebSocket Test
```bash
source .venv/bin/activate
python demo_system.py
```

---

## Environment Variables

Create `.env` in project root (use `.env.example` as template):

```bash
# LLM Provider (azure or ollama)
LLM_PROVIDER=azure

# Azure OpenAI (recommended)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Ollama (for local dev)
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2:latest

# APIs (optional)
COINGECKO_API_KEY=optional-for-higher-rate-limits
BITGET_API_KEY=optional-for-trading
BITGET_API_SECRET=optional-for-trading
BITGET_PASSPHRASE=optional-for-trading

# Agent Config
MAX_TURNS=15
MAX_STALLS=3
OUTPUT_DIR=./outputs
```

---

## Available Commands

| Command | Description |
|---------|-------------|
| `make dev` | Docker development mode |
| `make dev-local` | Local mode (hot reload) |
| `make dev-backend` | Backend only (local) |
| `make dev-frontend` | Frontend only (local) |
| `make prod` | Production mode |
| `make stop` | Stop all services |
| `make logs` | View container logs |
| `make status` | Check container status |

---

## Project Structure

```
MagenticOne/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── main.py           # Entry point
│   │   ├── api/
│   │   │   ├── routes/       # REST endpoints
│   │   │   │   ├── health.py
│   │   │   │   ├── chat.py
│   │   │   │   └── charts.py
│   │   │   └── websocket/
│   │   │       └── stream.py # WebSocket endpoint ⭐
│   │   ├── core/
│   │   │   ├── config.py     # Settings
│   │   │   └── dependencies.py
│   │   ├── models/
│   │   │   ├── events.py     # WebSocket event models ⭐
│   │   │   ├── requests.py
│   │   │   └── responses.py
│   │   └── services/
│   │       └── agent_service.py # MagenticOne adapter ⭐
│   └── requirements.txt
│
├── frontend/          # React + Vite frontend
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   └── features/
│   │   │       ├── ChatPanel.tsx
│   │   │       ├── StatusPanel.tsx
│   │   │       ├── ResultsPanel.tsx
│   │   │       └── ChartPanel.tsx
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts # WebSocket hook ⭐
│   │   ├── stores/
│   │   │   ├── chatStore.ts
│   │   │   ├── statusStore.ts
│   │   │   └── chartStore.ts
│   │   ├── services/
│   │   │   └── websocket.ts
│   │   └── types/
│   │       ├── api.ts
│   │       └── websocket.ts
│   └── package.json
│
├── src/               # Original console code
│   ├── main.py       # Console entry (still works!)
│   ├── crypto_tools.py
│   ├── exchange_tools.py
│   ├── cache.py      # TTLCache ⭐
│   └── ...
│
├── tests/            # Pytest tests ⭐
│   ├── conftest.py
│   ├── test_crypto_tools.py
│   └── test_exchange_tools.py
│
└── docs/
    ├── api/
    │   └── openapi.yaml # Full API spec ⭐
    └── migration/
        ├── PROGRESS.md       # Status tracker ⭐
        ├── CHECKLIST.md      # Task list
        ├── PHASE_3_COMPLETE.md
        └── QUICK_START.md    # This file
```

⭐ = Created/enhanced in Phases 0-3

---

## Common Issues & Solutions

### 1. Backend Won't Start
```bash
# Kill any process on port 8500
lsof -ti:8500 | xargs kill -9

# Check Python path
which python
# Should be: /workspaces/MagenticOne/.venv/bin/python

# Reinstall dependencies if needed
uv pip install fastapi uvicorn websockets pydantic
```

### 2. WebSocket Disconnects Immediately
- Check backend logs: `tail -f /tmp/backend.log`
- Verify PYTHONPATH is set when running uvicorn
- Make sure no `--reload` flag if files are changing

### 3. Import Errors in Backend
The backend uses absolute imports (`from app.api.routes import ...`), so PYTHONPATH must include `/workspaces/MagenticOne/backend`:

```bash
PYTHONPATH=/workspaces/MagenticOne/backend python -m uvicorn app.main:app --port 8500
```

### 4. Frontend Can't Connect
- Backend must be running on port 8500
- Check Vite proxy config in `frontend/vite.config.ts`
- Verify WebSocket URL in frontend `.env`: `VITE_WS_URL=ws://localhost:8500`

### 5. Tests Fail
```bash
# Recreate venv
cd /workspaces/MagenticOne
rm -rf .venv
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

---

## API Endpoints Summary

### Health
- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/ready` - Readiness (includes LLM check)
- `GET /api/v1/health/live` - Liveness probe

### WebSocket
- `WS /ws/stream` - Real-time agent streaming
- `GET /ws/status` - Connection count

### Chat
- `GET /api/v1/chat/` - List conversations
- `POST /api/v1/chat/` - Send message (background)
- `POST /api/v1/chat/new` - New conversation
- `GET /api/v1/chat/{id}` - Get history
- `GET /api/v1/chat/{id}/status` - Processing status
- `DELETE /api/v1/chat/{id}` - Delete

### Charts
- `GET /api/v1/charts/` - List charts
- `POST /api/v1/charts/` - Generate chart
- `GET /api/v1/charts/{id}` - Get details
- `DELETE /api/v1/charts/{id}` - Delete
- `POST /api/v1/charts/multi-timeframe` - Multi-TF dashboard
- `POST /api/v1/charts/alerts-dashboard` - AI alerts

---

## Next Steps (Phase 4)

1. **Set up Azure Key Vault** for secrets
2. **Create Settings API** for API key management
3. **Build Settings UI** in frontend
4. **Test with real Azure OpenAI** credentials
5. **Add conversation persistence** (database or files)

See `docs/migration/PHASE_4_SECRETS.md` for detailed plan.

---

## Getting Help

- **Migration docs**: `docs/migration/`
- **API spec**: `docs/api/openapi.yaml`
- **Phase status**: `docs/migration/PROGRESS.md`
- **Task list**: `docs/migration/CHECKLIST.md`
- **Phase 3 details**: `docs/migration/PHASE_3_COMPLETE.md`

---

**Last Updated**: November 30, 2025  
**Current Phase**: 3 (Complete) → Moving to Phase 4
