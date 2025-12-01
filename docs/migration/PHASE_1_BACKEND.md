# Phase 1: Backend API Implementation

> **Status: ✅ Complete**
> 
> **Completed:** 2025-11-30
> - FastAPI application ✅ (`backend/app/main.py`)
> - Health endpoints ✅ (`/api/v1/health`, `/api/v1/health/ready`)
> - Chat endpoints ✅ (`/api/v1/chat`)
> - Charts endpoints ✅ (`/api/v1/charts`)
> - Settings endpoints ✅ (`/api/v1/settings`)
> - WebSocket endpoint ✅ (`/api/v1/ws`)
> - Configuration ✅ (`backend/app/core/config.py`)

## Overview

Transform the console-based MagenticOne application into a FastAPI backend with WebSocket support.

---

## Step 1.1: Directory Structure

Create the following structure:

```bash
mkdir -p backend/app/{api/{routes,websocket},core,services,models,utils}
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/api/routes/__init__.py
touch backend/app/api/websocket/__init__.py
touch backend/app/core/__init__.py
touch backend/app/services/__init__.py
touch backend/app/models/__init__.py
touch backend/app/utils/__init__.py
```

---

## Step 1.2: Requirements

```txt
# backend/requirements.txt

# Web Framework
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.6

# WebSocket
websockets>=12.0

# Security
cryptography>=42.0.0
python-jose[cryptography]>=3.3.0

# Validation
pydantic>=2.5.0
pydantic-settings>=2.1.0

# Async
aiofiles>=23.2.0
httpx>=0.26.0

# Include existing dependencies
autogen-agentchat>=0.4.0
autogen-ext[magentic-one]>=0.4.0
openai>=1.12.0
tiktoken>=0.5.0
requests>=2.31.0
aiohttp>=3.9.0
python-dotenv>=1.0.0
rich>=13.7.0
pyyaml>=6.0.1
pandas>=2.0.0
numpy>=1.24.0
plotly>=5.18.0
kaleido>=0.2.1
```

---

## Step 1.3: Main FastAPI Application

```python
# backend/app/main.py
"""
MagenticOne Crypto Analysis - FastAPI Backend

Main application entry point with REST and WebSocket support.
"""
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Add src to path for existing modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from app.api.routes import chat, charts, settings, health
from app.api.websocket import stream
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings = get_settings()
    print(f"🚀 Starting MagenticOne API (Provider: {settings.llm_provider})")
    
    yield
    
    # Shutdown
    print("👋 Shutting down MagenticOne API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="MagenticOne Crypto Analysis API",
        description="Multi-agent cryptocurrency analysis platform",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
    app.include_router(charts.router, prefix="/api/v1/charts", tags=["Charts"])
    app.include_router(settings.router, prefix="/api/v1/settings", tags=["Settings"])
    
    # WebSocket
    app.include_router(stream.router, tags=["WebSocket"])
    
    # Static files for charts
    charts_dir = Path("outputs/charts")
    charts_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/charts", StaticFiles(directory=str(charts_dir)), name="charts")
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

---

## Step 1.4: Configuration

```python
# backend/app/core/config.py
"""
Application configuration using Pydantic Settings.
"""
from functools import lru_cache
from typing import List, Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # API Settings
    api_title: str = "MagenticOne Crypto Analysis API"
    api_version: str = "1.0.0"
    debug: bool = False
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # LLM Provider
    llm_provider: Literal["ollama", "azure"] = "ollama"
    
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gpt-oss:20b"
    ollama_temperature: float = 0.7
    
    # Azure OpenAI
    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-02-15-preview"
    
    # Agent Settings
    max_turns: int = 20
    max_stalls: int = 3
    
    # Output
    output_dir: str = "outputs"
    
    # Secrets
    secrets_dir: str = "/app/data"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

---

## Step 1.5: Health Endpoints

```python
# backend/app/api/routes/health.py
"""
Health check endpoints for container orchestration.
"""
from datetime import datetime
from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/health/ready")
async def readiness_check(settings: Settings = Depends(get_settings)):
    """
    Readiness check - verifies dependencies are available.
    """
    checks = {
        "api": True,
        "llm_provider": settings.llm_provider,
    }
    
    # Check LLM availability
    if settings.llm_provider == "ollama":
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags", timeout=5.0)
                checks["ollama"] = resp.status_code == 200
        except Exception:
            checks["ollama"] = False
    
    all_healthy = all(v for v in checks.values() if isinstance(v, bool))
    
    return {
        "status": "ready" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/health/live")
async def liveness_check():
    """Liveness check - just confirms the process is running."""
    return {"status": "alive"}
```

---

## Step 1.6: Pydantic Models

```python
# backend/app/models/requests.py
"""
Request models for API endpoints.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A chat message from the user."""
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: Optional[str] = None


class ChartRequest(BaseModel):
    """Request to generate a chart."""
    symbol: str = Field(..., example="BTCUSDT")
    interval: str = Field(default="1H", example="1H")
    indicators: List[str] = Field(default=["volume"], example=["rsi", "macd"])
    theme: str = Field(default="dark")


class ExchangeCredentials(BaseModel):
    """Exchange API credentials (Bitget)."""
    api_key: str = Field(..., min_length=1)
    api_secret: str = Field(..., min_length=1)
    passphrase: str = Field(..., min_length=1)


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    provider: str = Field(..., pattern="^(ollama|azure)$")
    model: Optional[str] = None
    base_url: Optional[str] = None
```

```python
# backend/app/models/responses.py
"""
Response models for API endpoints.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class ChatResponse(BaseModel):
    """Response from a chat request (REST, non-streaming)."""
    conversation_id: str
    message: str
    agents_used: List[str]
    charts_generated: List[str] = []
    timestamp: datetime


class ChartResponse(BaseModel):
    """Response from chart generation."""
    chart_id: str
    file_path: str
    url: str
    symbol: str
    interval: str


class StatusResponse(BaseModel):
    """Generic status response."""
    status: str
    message: str
    details: Optional[Dict[str, Any]] = None
```

```python
# backend/app/models/events.py
"""
WebSocket event models.
"""
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel


class AgentStepEvent(BaseModel):
    """Event when an agent starts working."""
    type: Literal["agent_step"] = "agent_step"
    agent: str
    emoji: str
    status: str  # "working", "completed", "error"
    timestamp: datetime


class ToolCallEvent(BaseModel):
    """Event when a tool is called."""
    type: Literal["tool_call"] = "tool_call"
    agent: str
    tool_name: str
    arguments: Optional[Dict[str, Any]] = None
    timestamp: datetime


class ToolResultEvent(BaseModel):
    """Event when a tool returns a result."""
    type: Literal["tool_result"] = "tool_result"
    tool_name: str
    success: bool
    result_preview: Optional[str] = None
    timestamp: datetime


class ChartGeneratedEvent(BaseModel):
    """Event when a chart is generated."""
    type: Literal["chart"] = "chart"
    chart_id: str
    url: str
    symbol: str
    timestamp: datetime


class FinalResultEvent(BaseModel):
    """Event with the final answer."""
    type: Literal["result"] = "result"
    content: str
    format: str = "markdown"
    agents_used: List[str]
    timestamp: datetime


class ErrorEvent(BaseModel):
    """Event when an error occurs."""
    type: Literal["error"] = "error"
    message: str
    details: Optional[str] = None
    timestamp: datetime


class ProgressEvent(BaseModel):
    """Event for progress updates."""
    type: Literal["progress"] = "progress"
    current_turn: int
    max_turns: int
    percentage: float
    timestamp: datetime
```

---

## Step 1.7: WebSocket Stream Handler

```python
# backend/app/api/websocket/stream.py
"""
WebSocket endpoint for real-time agent streaming.
"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.events import (
    AgentStepEvent,
    ToolCallEvent,
    FinalResultEvent,
    ErrorEvent,
    ProgressEvent,
)
from app.services.agent_service import AgentService

router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)
    
    async def send_event(self, client_id: str, event: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(event)


manager = ConnectionManager()


@router.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for streaming agent interactions.
    
    Client sends: {"type": "chat", "payload": {"message": "..."}}
    Server sends: AgentStepEvent, ToolCallEvent, FinalResultEvent, etc.
    """
    client_id = str(uuid.uuid4())
    await manager.connect(websocket, client_id)
    
    agent_service = AgentService()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            if data.get("type") == "chat":
                message = data.get("payload", {}).get("message", "")
                
                if not message:
                    await manager.send_event(client_id, ErrorEvent(
                        message="Empty message",
                        timestamp=datetime.now()
                    ).model_dump())
                    continue
                
                # Stream agent responses
                async for event in agent_service.run_streaming(message):
                    await manager.send_event(client_id, event.model_dump())
            
            elif data.get("type") == "cancel":
                # Cancel current task
                await agent_service.cancel()
                await manager.send_event(client_id, {
                    "type": "cancelled",
                    "timestamp": datetime.now().isoformat()
                })
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        await manager.send_event(client_id, ErrorEvent(
            message=str(e),
            timestamp=datetime.now()
        ).model_dump())
        manager.disconnect(client_id)
```

---

## Step 1.8: Agent Service (Stream Adapter)

This is the critical component that converts console output to WebSocket events:

```python
# backend/app/services/agent_service.py
"""
Agent Service - Wraps MagenticOne for API use.

This is the critical adapter that converts the console-based
CryptoAnalysisPlatform into a streaming API service.
"""
import asyncio
from datetime import datetime
from typing import AsyncIterator, Optional, List, Dict, Any
from pathlib import Path

from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import (
    TextMessage,
    ThoughtEvent,
    ToolCallRequestEvent,
    ToolCallExecutionEvent,
    StopMessage,
)
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor

from app.core.config import get_settings
from app.models.events import (
    AgentStepEvent,
    ToolCallEvent,
    ToolResultEvent,
    FinalResultEvent,
    ErrorEvent,
    ProgressEvent,
    ChartGeneratedEvent,
)

# Agent emojis for UI
AGENT_EMOJIS = {
    'CryptoMarketAnalyst': '📊',
    'TechnicalAnalyst': '📈',
    'CryptoAnalysisCoder': '👨‍💻',
    'ReportWriter': '📝',
    'ChartingAgent': '📉',
    'Executor': '🖥️',
}


class AgentService:
    """
    Service for running MagenticOne agents with streaming output.
    
    Converts the Rich console output pattern to WebSocket events.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.model_client = self._create_model_client()
        self.conversation_history: List[Dict[str, str]] = []
        self._current_task: Optional[asyncio.Task] = None
        self._cancelled = False
    
    def _create_model_client(self):
        """Create the appropriate LLM client."""
        if self.settings.llm_provider == "azure":
            from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
            return AzureOpenAIChatCompletionClient(
                azure_deployment=self.settings.azure_openai_deployment,
                api_version=self.settings.azure_openai_api_version,
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                model=self.settings.azure_openai_deployment,
                model_info={"function_calling": True, "vision": True},
            )
        else:
            from ollama_client import OllamaChatCompletionClient
            return OllamaChatCompletionClient(
                model=self.settings.ollama_model,
                base_url=self.settings.ollama_base_url,
                temperature=self.settings.ollama_temperature,
            )
    
    async def _create_team(self) -> MagenticOneGroupChat:
        """Create the MagenticOne team with all agents."""
        # Import tools
        from crypto_tools import get_crypto_price, get_historical_data, get_market_info
        from crypto_charts import create_crypto_chart
        from exchange_tools import (
            get_realtime_price, get_price_comparison, get_orderbook_depth,
            get_ohlcv_data, get_recent_market_trades, get_futures_data,
            get_futures_candles, get_account_balance, check_exchange_status,
        )
        from report_tools import (
            save_markdown_report, create_analysis_report,
            create_comparison_report, create_custom_indicator_report,
        )
        from indicator_registry import (
            save_custom_indicator, list_custom_indicators,
            get_custom_indicator, delete_custom_indicator,
            get_indicator_code_for_execution,
        )
        from tradingview_tools import (
            generate_tradingview_chart, create_ai_annotated_chart,
            generate_multi_timeframe_dashboard, generate_strategy_backtest_chart,
        )
        from smart_alerts import generate_smart_alerts_dashboard, create_trade_idea_alert
        
        # Define tool sets
        coingecko_tools = [get_crypto_price, get_historical_data, get_market_info, create_crypto_chart]
        exchange_tools = [
            get_realtime_price, get_price_comparison, get_orderbook_depth,
            get_ohlcv_data, get_recent_market_trades, get_futures_data,
            get_futures_candles, get_account_balance, check_exchange_status,
        ]
        report_tools = [save_markdown_report, create_analysis_report, create_comparison_report, create_custom_indicator_report]
        indicator_tools = [save_custom_indicator, list_custom_indicators, get_custom_indicator, delete_custom_indicator, get_indicator_code_for_execution]
        tradingview_tools_list = [generate_tradingview_chart, create_ai_annotated_chart, generate_multi_timeframe_dashboard, generate_strategy_backtest_chart, generate_smart_alerts_dashboard, create_trade_idea_alert]
        
        all_crypto_tools = coingecko_tools + exchange_tools
        
        # Create agents (using existing system messages from main.py)
        market_analyst = AssistantAgent(
            "CryptoMarketAnalyst",
            model_client=self.model_client,
            tools=all_crypto_tools,
            system_message="You are a cryptocurrency market analyst...",  # Abbreviated
            description="Expert in crypto markets and trends",
        )
        
        technical_analyst = AssistantAgent(
            "TechnicalAnalyst",
            model_client=self.model_client,
            tools=all_crypto_tools + indicator_tools,
            system_message="You are a cryptocurrency technical analyst...",
            description="Expert in technical analysis and charts",
        )
        
        charting_agent = AssistantAgent(
            "ChartingAgent",
            model_client=self.model_client,
            tools=tradingview_tools_list + exchange_tools,
            system_message="You are a professional charting specialist...",
            description="TradingView charting specialist",
        )
        
        coder = AssistantAgent(
            "CryptoAnalysisCoder",
            model_client=self.model_client,
            tools=indicator_tools,
            system_message="You are a Python developer for crypto analysis...",
            description="Python developer for analysis and backtesting",
        )
        
        report_writer = AssistantAgent(
            "ReportWriter",
            model_client=self.model_client,
            tools=report_tools,
            system_message="You are a professional report writer...",
            description="Report writer for analysis documents",
        )
        
        code_executor = LocalCommandLineCodeExecutor(
            work_dir=str(Path(self.settings.output_dir) / "code_execution"),
        )
        executor = CodeExecutorAgent("Executor", code_executor=code_executor)
        
        return MagenticOneGroupChat(
            participants=[market_analyst, technical_analyst, charting_agent, coder, report_writer, executor],
            model_client=self.model_client,
            max_turns=self.settings.max_turns,
            max_stalls=self.settings.max_stalls,
        )
    
    async def run_streaming(self, message: str) -> AsyncIterator:
        """
        Run an agent task with streaming events.
        
        This is the key method that converts console output to events.
        
        Yields:
            WebSocket events (AgentStepEvent, ToolCallEvent, etc.)
        """
        self._cancelled = False
        team = await self._create_team()
        
        last_agent = None
        turn_count = 0
        agents_used = []
        
        try:
            async for msg in team.run_stream(task=message):
                if self._cancelled:
                    break
                
                # Track TaskResult
                if isinstance(msg, TaskResult):
                    # Extract final answer
                    for m in reversed(msg.messages):
                        if isinstance(m, (TextMessage, StopMessage)):
                            content = getattr(m, 'content', str(m))
                            if content and not content.startswith("TERMINATE"):
                                yield FinalResultEvent(
                                    content=content,
                                    format="markdown",
                                    agents_used=agents_used,
                                    timestamp=datetime.now(),
                                )
                                break
                    continue
                
                # Get source/agent name
                source = getattr(msg, 'source', None)
                
                # Emit agent step event
                if source and source != last_agent:
                    turn_count += 1
                    if source not in agents_used:
                        agents_used.append(source)
                    
                    yield AgentStepEvent(
                        agent=source,
                        emoji=AGENT_EMOJIS.get(source, '🤖'),
                        status="working",
                        timestamp=datetime.now(),
                    )
                    
                    yield ProgressEvent(
                        current_turn=turn_count,
                        max_turns=self.settings.max_turns,
                        percentage=(turn_count / self.settings.max_turns) * 100,
                        timestamp=datetime.now(),
                    )
                    
                    last_agent = source
                
                # Emit tool call events
                if isinstance(msg, ToolCallRequestEvent):
                    for call in msg.content:
                        tool_name = call.name if hasattr(call, 'name') else str(call)
                        yield ToolCallEvent(
                            agent=source or "unknown",
                            tool_name=tool_name,
                            timestamp=datetime.now(),
                        )
                        
                        # Check if it's a chart generation tool
                        if 'chart' in tool_name.lower():
                            # Will emit ChartGeneratedEvent when tool completes
                            pass
                
                if isinstance(msg, ToolCallExecutionEvent):
                    for result in msg.content:
                        yield ToolResultEvent(
                            tool_name=result.call_id if hasattr(result, 'call_id') else "unknown",
                            success=True,
                            result_preview=str(result.content)[:200] if hasattr(result, 'content') else None,
                            timestamp=datetime.now(),
                        )
        
        except asyncio.CancelledError:
            yield ErrorEvent(
                message="Task cancelled by user",
                timestamp=datetime.now(),
            )
        except Exception as e:
            yield ErrorEvent(
                message=str(e),
                details=str(type(e).__name__),
                timestamp=datetime.now(),
            )
    
    async def cancel(self):
        """Cancel the current running task."""
        self._cancelled = True
```

---

## Next Steps

After completing Phase 1, proceed to:
- [Phase 2: Frontend Application](./PHASE_2_FRONTEND.md)

---

*Document created: 2025-11-29*
