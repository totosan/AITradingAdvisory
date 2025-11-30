# 🚀 MagenticOne Web Application Migration Plan

## Executive Summary

Transform the existing console-based MagenticOne Crypto Analysis Platform into a modern, containerized web application ready for Azure deployment.

**Current State:** Console-based Python application with Rich UI  
**Target State:** Full-stack web application with REST API backend + React frontend

**Migration Status:** 🔄 In Progress - See [PROGRESS.md](./PROGRESS.md) for current state

---

## 📋 Table of Contents

0. [Phase 0: Pre-Migration Preparation](#phase-0-pre-migration-preparation) *(New)*
1. [Phase 1: Backend API](#phase-1-backend-api)
2. [Phase 2: Frontend Application](#phase-2-frontend-application)
3. [Phase 3: Real-time Communication](#phase-3-real-time-communication)
4. [Phase 4: Secrets Management](#phase-4-secrets-management)
5. [Phase 5: Containerization & Azure Prep](#phase-5-containerization--azure-prep)
6. [Phase 6: Post-Launch](#phase-6-post-launch) *(New)*
7. [File Structure](#file-structure)
8. [Migration Steps](#migration-steps)

### Related Documents

| Document | Purpose |
|----------|---------|
| [CHECKLIST.md](./CHECKLIST.md) | Task tracking checklist |
| [PROGRESS.md](./PROGRESS.md) | Session log and status |
| [PHASE_0_PREPARATION.md](./PHASE_0_PREPARATION.md) | Pre-migration tasks |
| [PHASE_1_BACKEND.md](./PHASE_1_BACKEND.md) | Backend implementation |
| [PHASE_2_FRONTEND.md](./PHASE_2_FRONTEND.md) | Frontend implementation |
| [PHASE_3_REALTIME.md](./PHASE_3_REALTIME.md) | WebSocket details |
| [PHASE_4_SECRETS.md](./PHASE_4_SECRETS.md) | Security implementation |
| [PHASE_5_CONTAINERS.md](./PHASE_5_CONTAINERS.md) | Docker & Azure |

---

## 🏗️ Architecture Overview

### Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React/Vite)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │  Results     │  │   Chat Box   │  │   Status     │  │  Charting Panel  │ │
│  │  Display     │  │  (WebSocket) │  │   Panel      │  │  (TradingView)   │ │
│  │  (Markdown)  │  │              │  │  (Progress)  │  │  (Right Side)    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │ WebSocket + REST
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            BACKEND (FastAPI)                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────────┐ │
│  │  REST API        │  │  WebSocket Hub   │  │  Agent Orchestrator        │ │
│  │  /api/chat       │  │  /ws/stream      │  │  (MagenticOne)             │ │
│  │  /api/settings   │  │  Real-time msgs  │  │  6 Specialized Agents      │ │
│  └──────────────────┘  └──────────────────┘  └────────────────────────────┘ │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────────┐ │
│  │  Secrets Vault   │  │  Chart Generator │  │  Exchange Manager          │ │
│  │  (Encrypted)     │  │  (TradingView)   │  │  (Bitget/CoinGecko)        │ │
│  └──────────────────┘  └──────────────────┘  └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                ▼                   ▼                   ▼
         ┌──────────┐        ┌──────────┐        ┌──────────┐
         │  Ollama  │        │  Azure   │        │ Exchange │
         │   LLM    │        │  OpenAI  │        │   APIs   │
         └──────────┘        └──────────┘        └──────────┘
```

### Technology Stack

| Layer | Technology | Justification |
|-------|------------|---------------|
| Frontend | React 18 + TypeScript + Vite | Modern, fast, type-safe |
| UI Components | shadcn/ui + Tailwind CSS | Professional, customizable |
| Charting | Lightweight Charts (TradingView) | Already used, proven |
| Backend | FastAPI + Python 3.11 | Async, fast, existing codebase |
| Real-time | WebSockets | Bi-directional, low latency |
| Secrets | Fernet encryption + keyring | Secure, container-ready |
| Container | Docker + Docker Compose | Azure-ready, portable |

---

## 📡 Phase 1: Backend API

### 1.1 FastAPI Application Structure

Create a new `backend/` directory with modular API structure:

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── chat.py      # Chat/analysis endpoints
│   │   │   ├── charts.py    # Chart generation endpoints
│   │   │   ├── settings.py  # Settings/secrets endpoints
│   │   │   └── health.py    # Health checks
│   │   └── websocket/
│   │       └── stream.py    # WebSocket for real-time updates
│   ├── core/
│   │   ├── config.py        # Pydantic settings
│   │   ├── security.py      # Encryption/secrets
│   │   └── dependencies.py  # FastAPI dependencies
│   ├── services/
│   │   ├── agent_service.py # MagenticOne orchestration
│   │   ├── chart_service.py # Chart generation
│   │   └── exchange_service.py
│   ├── models/
│   │   ├── requests.py      # Pydantic request models
│   │   ├── responses.py     # Pydantic response models
│   │   └── events.py        # WebSocket event models
│   └── utils/
│       └── stream_adapter.py # Console → WebSocket adapter
├── requirements.txt
└── Dockerfile
```

### 1.2 Key API Endpoints

```python
# Chat/Analysis
POST /api/v1/chat/message          # Send message, get streaming response
GET  /api/v1/chat/history          # Get conversation history
POST /api/v1/chat/clear            # Clear conversation

# Charts
POST /api/v1/charts/generate       # Generate a chart
GET  /api/v1/charts/{chart_id}     # Get chart data
GET  /api/v1/charts/list           # List available charts

# Settings (Secrets)
POST /api/v1/settings/exchange     # Save exchange credentials (encrypted)
GET  /api/v1/settings/exchange     # Get exchange status (not secrets)
POST /api/v1/settings/llm          # Configure LLM provider

# Health
GET  /api/v1/health                # Health check for containers
GET  /api/v1/health/ready          # Readiness probe
```

### 1.3 WebSocket Events

```typescript
// Client → Server
interface ClientMessage {
  type: "chat" | "cancel" | "subscribe";
  payload: {
    message?: string;
    symbols?: string[];  // For real-time price subscriptions
  };
}

// Server → Client
interface ServerEvent {
  type: "agent_step" | "tool_call" | "result" | "chart" | "error" | "status";
  payload: {
    agent?: string;
    content?: string;
    progress?: number;
    chartData?: ChartData;
  };
}
```

### 1.4 Stream Adapter (Console → WebSocket)

The key innovation is converting the Rich console output to WebSocket events:

```python
# Current: Console output
self.console.print(f"\n{agent_emoji} [bold cyan]{source}[/bold cyan] is working...")

# New: WebSocket event emission
await websocket.send_json({
    "type": "agent_step",
    "payload": {
        "agent": source,
        "emoji": agent_emoji,
        "status": "working",
        "timestamp": datetime.now().isoformat()
    }
})
```

---

## 🎨 Phase 2: Frontend Application

### 2.1 Frontend Structure

```
frontend/
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   ├── components/
│   │   ├── layout/
│   │   │   ├── MainLayout.tsx       # Main 4-panel layout
│   │   │   ├── Header.tsx
│   │   │   └── Sidebar.tsx
│   │   ├── chat/
│   │   │   ├── ChatBox.tsx          # Message input + history
│   │   │   ├── MessageBubble.tsx    # Individual messages
│   │   │   └── TypingIndicator.tsx
│   │   ├── results/
│   │   │   ├── ResultsPanel.tsx     # Formatted results display
│   │   │   ├── MarkdownRenderer.tsx # Rich markdown
│   │   │   └── TableRenderer.tsx    # Data tables
│   │   ├── status/
│   │   │   ├── StatusPanel.tsx      # Agent status display
│   │   │   ├── AgentCard.tsx        # Individual agent status
│   │   │   └── ProgressBar.tsx
│   │   ├── charts/
│   │   │   ├── ChartPanel.tsx       # TradingView wrapper
│   │   │   ├── ChartControls.tsx    # Timeframe/indicators
│   │   │   └── MiniChart.tsx        # Small embedded charts
│   │   └── settings/
│   │       ├── SettingsDialog.tsx
│   │       ├── ExchangeSettings.tsx # Bitget keys input
│   │       └── LLMSettings.tsx
│   ├── hooks/
│   │   ├── useWebSocket.ts          # WebSocket management
│   │   ├── useChat.ts               # Chat state
│   │   └── useAgentStatus.ts        # Agent tracking
│   ├── services/
│   │   ├── api.ts                   # REST API client
│   │   └── websocket.ts             # WebSocket client
│   ├── stores/
│   │   ├── chatStore.ts             # Zustand store
│   │   ├── statusStore.ts
│   │   └── chartStore.ts
│   └── types/
│       ├── api.ts
│       └── websocket.ts
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── Dockerfile
```

### 2.2 Main Layout Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🪙 Crypto Analysis Platform                          ⚙️ Settings  🌙 Theme │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────────────┤
│  │                             │  │                                         │
│  │      📊 Results Panel       │  │         📈 Chart Panel                  │
│  │                             │  │                                         │
│  │   Well-formatted analysis   │  │    TradingView Lightweight Charts       │
│  │   Markdown rendering        │  │    Multiple timeframes                  │
│  │   Tables, bullets, etc.     │  │    Indicators overlay                   │
│  │                             │  │                                         │
│  ├─────────────────────────────┤  │                                         │
│  │                             │  │                                         │
│  │      📋 Status Panel        │  │                                         │
│  │                             │  │                                         │
│  │   Agent: 📊 MarketAnalyst   │  │                                         │
│  │   Status: Fetching data...  │  │                                         │
│  │   ████████░░ 80%            │  │                                         │
│  │                             │  │                                         │
│  ├─────────────────────────────┤  ├─────────────────────────────────────────┤
│  │                             │  │   Chart Controls: BTC ▼  1H ▼  📊 RSI  │
│  │      💬 Chat Box            │  └─────────────────────────────────────────┤
│  │                             │
│  │   [Type your question...]   │
│  │                             │
│  └─────────────────────────────┘
│
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Key Components

#### ResultsPanel - Formatted Display

Instead of raw console output, results are beautifully rendered:

```tsx
// Convert agent output to rich components
const ResultsPanel: React.FC = () => {
  return (
    <div className="results-panel">
      {/* Summary Card */}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle>📊 Bitcoin Analysis Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <MetricsGrid>
            <Metric label="Price" value="$95,420" trend="up" />
            <Metric label="24h Change" value="+2.5%" trend="up" />
            <Metric label="RSI" value="62" status="neutral" />
          </MetricsGrid>
        </CardContent>
      </Card>
      
      {/* Detailed Analysis */}
      <MarkdownRenderer content={analysisMarkdown} />
      
      {/* Embedded Mini-Charts */}
      <MiniChartGrid charts={generatedCharts} />
    </div>
  );
};
```

#### StatusPanel - Agent Progress

```tsx
const StatusPanel: React.FC = () => {
  const { activeAgent, progress, toolCalls } = useAgentStatus();
  
  return (
    <div className="status-panel">
      <AgentStatus 
        agent={activeAgent}
        emoji={agentEmojis[activeAgent]}
        status="working"
      />
      <ProgressBar value={progress} />
      <ToolCallLog calls={toolCalls} />
    </div>
  );
};
```

---

## 🔌 Phase 3: Real-time Communication

### 3.1 WebSocket Connection Management

```typescript
// frontend/src/hooks/useWebSocket.ts
export function useWebSocket() {
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const socketRef = useRef<WebSocket | null>(null);
  
  const connect = useCallback(() => {
    const ws = new WebSocket(`${WS_URL}/ws/stream`);
    
    ws.onopen = () => setStatus('connected');
    ws.onclose = () => {
      setStatus('disconnected');
      // Auto-reconnect with exponential backoff
      setTimeout(connect, 1000);
    };
    
    ws.onmessage = (event) => {
      const data: ServerEvent = JSON.parse(event.data);
      handleServerEvent(data);
    };
    
    socketRef.current = ws;
  }, []);
  
  return { status, connect, send: (msg) => socketRef.current?.send(JSON.stringify(msg)) };
}
```

### 3.2 Backend WebSocket Handler

```python
# backend/app/api/websocket/stream.py
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def broadcast_agent_event(self, event: AgentEvent):
        for connection in self.active_connections:
            await connection.send_json(event.dict())

@router.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data["type"] == "chat":
                # Run agent task with streaming output
                async for event in run_agent_streaming(data["payload"]["message"]):
                    await websocket.send_json(event.dict())
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

---

## 🔐 Phase 4: Secrets Management

### 4.1 Encryption Service

```python
# backend/app/core/security.py
from cryptography.fernet import Fernet
from pathlib import Path
import json

class SecretsVault:
    """Secure secrets storage with Fernet encryption."""
    
    def __init__(self, key_file: Path = Path("/app/data/.key")):
        self.key_file = key_file
        self.secrets_file = key_file.parent / ".secrets.enc"
        self._fernet = self._load_or_create_key()
    
    def _load_or_create_key(self) -> Fernet:
        if self.key_file.exists():
            key = self.key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            self.key_file.parent.mkdir(parents=True, exist_ok=True)
            self.key_file.write_bytes(key)
            self.key_file.chmod(0o600)  # Owner read/write only
        return Fernet(key)
    
    def save_secret(self, key: str, value: str) -> None:
        secrets = self._load_secrets()
        secrets[key] = value
        encrypted = self._fernet.encrypt(json.dumps(secrets).encode())
        self.secrets_file.write_bytes(encrypted)
    
    def get_secret(self, key: str) -> Optional[str]:
        secrets = self._load_secrets()
        return secrets.get(key)
```

### 4.2 Settings API

```python
# backend/app/api/routes/settings.py
@router.post("/exchange")
async def save_exchange_credentials(
    credentials: ExchangeCredentials,
    vault: SecretsVault = Depends(get_vault)
):
    """Save encrypted exchange credentials."""
    vault.save_secret("bitget_api_key", credentials.api_key)
    vault.save_secret("bitget_api_secret", credentials.api_secret)
    vault.save_secret("bitget_passphrase", credentials.passphrase)
    
    # Validate credentials work
    try:
        await validate_bitget_credentials(credentials)
        return {"status": "success", "message": "Credentials saved and validated"}
    except Exception as e:
        return {"status": "warning", "message": f"Saved but validation failed: {e}"}
```

### 4.3 Frontend Settings Dialog

```tsx
const ExchangeSettings: React.FC = () => {
  const [credentials, setCredentials] = useState({
    apiKey: '',
    apiSecret: '',
    passphrase: ''
  });
  
  const handleSave = async () => {
    const response = await api.post('/settings/exchange', credentials);
    if (response.status === 'success') {
      toast.success('Exchange credentials saved securely');
    }
  };
  
  return (
    <Dialog>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>🔶 Bitget Exchange Settings</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <Input 
            type="password" 
            placeholder="API Key"
            value={credentials.apiKey}
            onChange={(e) => setCredentials({...credentials, apiKey: e.target.value})}
          />
          <Input 
            type="password" 
            placeholder="API Secret"
            value={credentials.apiSecret}
            onChange={(e) => setCredentials({...credentials, apiSecret: e.target.value})}
          />
          <Input 
            type="password" 
            placeholder="Passphrase"
            value={credentials.passphrase}
            onChange={(e) => setCredentials({...credentials, passphrase: e.target.value})}
          />
          <Alert>
            <AlertDescription>
              🔒 Credentials are encrypted and stored securely in the container.
              They are never transmitted in plain text after saving.
            </AlertDescription>
          </Alert>
        </div>
        <Button onClick={handleSave}>Save Credentials</Button>
      </DialogContent>
    </Dialog>
  );
};
```

---

## 🐳 Phase 5: Containerization & Azure Prep

### 5.1 Docker Architecture

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - secrets-data:/app/data        # Encrypted secrets persist here
      - outputs:/app/outputs           # Charts, reports, etc.
    environment:
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
      - CORS_ORIGINS=http://localhost:3000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    depends_on:
      - backend
    environment:
      - VITE_API_URL=http://localhost:8000
      - VITE_WS_URL=ws://localhost:8000

  # Optional: Ollama for local development
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-models:/root/.ollama
    profiles:
      - with-ollama

volumes:
  secrets-data:
  outputs:
  ollama-models:
```

### 5.2 Backend Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY ../src/ ./src/  # Existing agent code

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 5.3 Frontend Dockerfile

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine as builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 5.4 Azure Container Apps Ready

The architecture is designed for Azure Container Apps:

```yaml
# azure/container-apps.yaml (future)
resources:
  - name: crypto-backend
    type: containerapp
    properties:
      configuration:
        ingress:
          external: false
          targetPort: 8000
        secrets:
          - name: azure-openai-key
            value: "@Microsoft.KeyVault(SecretUri=...)"
      template:
        containers:
          - image: cryptoanalysis.azurecr.io/backend:latest
            resources:
              cpu: 1
              memory: 2Gi
            
  - name: crypto-frontend
    type: containerapp
    properties:
      configuration:
        ingress:
          external: true
          targetPort: 80
```

---

## 📁 File Structure

### Final Project Structure

```
MagenticOne/
├── backend/                    # NEW: FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   ├── services/
│   │   ├── models/
│   │   └── utils/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                   # NEW: React frontend
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── stores/
│   │   └── types/
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
│
├── src/                        # EXISTING: Agent code (reused)
│   ├── config.py
│   ├── crypto_tools.py
│   ├── crypto_charts.py
│   ├── exchange_tools.py
│   ├── tradingview_tools.py
│   ├── smart_alerts.py
│   ├── report_tools.py
│   ├── indicator_registry.py
│   ├── ollama_client.py
│   └── exchange_providers/
│
├── docker-compose.yml          # UPDATED: Multi-service
├── docker-compose.dev.yml      # NEW: Dev environment
├── Makefile                    # UPDATED: New commands
│
├── docs/
│   └── migration/              # This documentation
│       ├── MIGRATION_PLAN.md
│       ├── PHASE_1_BACKEND.md
│       ├── PHASE_2_FRONTEND.md
│       └── ...
│
└── azure/                      # NEW: Azure deployment
    ├── bicep/
    └── container-apps.yaml
```

---

## 📋 Migration Steps

### Step-by-Step Execution Order

#### Week 1: Backend Foundation
- [ ] **Step 1.1**: Create `backend/` directory structure
- [ ] **Step 1.2**: Implement FastAPI app with health endpoints
- [ ] **Step 1.3**: Create WebSocket infrastructure
- [ ] **Step 1.4**: Build stream adapter (Console → WebSocket events)
- [ ] **Step 1.5**: Implement agent service wrapper
- [ ] **Step 1.6**: Add CORS and security middleware

#### Week 2: Backend Complete + Frontend Start
- [ ] **Step 2.1**: Implement chat API endpoints
- [ ] **Step 2.2**: Implement chart API endpoints
- [ ] **Step 2.3**: Build secrets vault with encryption
- [ ] **Step 2.4**: Implement settings endpoints
- [ ] **Step 2.5**: Create frontend project (Vite + React + TypeScript)
- [ ] **Step 2.6**: Setup Tailwind CSS + shadcn/ui

#### Week 3: Frontend Core
- [ ] **Step 3.1**: Build MainLayout component (4-panel grid)
- [ ] **Step 3.2**: Implement ChatBox with WebSocket
- [ ] **Step 3.3**: Build ResultsPanel with markdown rendering
- [ ] **Step 3.4**: Create StatusPanel with agent tracking
- [ ] **Step 3.5**: Integrate Lightweight Charts component

#### Week 4: Integration & Polish
- [ ] **Step 4.1**: Connect all frontend components to backend
- [ ] **Step 4.2**: Implement settings dialog
- [ ] **Step 4.3**: Add error handling and loading states
- [ ] **Step 4.4**: Update Docker Compose for multi-service
- [ ] **Step 4.5**: Test full flow end-to-end
- [ ] **Step 4.6**: Documentation and cleanup

---

## ✅ Success Criteria

1. **Backend API**: All endpoints working, WebSocket streaming functional
2. **Frontend**: All 4 panels rendering correctly with real data
3. **Real-time**: Agent steps visible in status panel as they happen
4. **Charts**: TradingView charts embedded and interactive
5. **Secrets**: Bitget credentials saveable and encrypted
6. **Containers**: `docker-compose up` brings up entire stack
7. **Azure-ready**: Can deploy to Azure Container Apps with minimal changes

---

## 🎯 Key Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend Framework | FastAPI | Async, Python, works with existing code |
| Frontend Framework | React + Vite | Modern, fast, great ecosystem |
| State Management | Zustand | Simple, lightweight, TypeScript |
| Styling | Tailwind + shadcn/ui | Rapid development, professional look |
| Charting | Lightweight Charts | Already used in codebase, proven |
| Secrets | Fernet encryption | Python native, simple, secure |
| Containerization | Docker Compose | Simple, Azure-compatible |

---

*Document created: 2025-11-29*
*Last updated: 2025-11-29*
