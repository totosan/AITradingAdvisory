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

from app.api.routes import health, chat, charts
from app.api.routes import settings as settings_router
from app.api.websocket import stream
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    # Startup
    settings = get_settings()
    print(f"🚀 Starting MagenticOne API")
    print(f"   Provider: {settings.llm_provider}")
    print(f"   Model: {settings.ollama_model if settings.llm_provider == 'ollama' else settings.azure_openai_deployment}")
    print(f"   WebSocket: ws://localhost:8000/ws/stream")
    
    yield
    
    # Shutdown
    print("👋 Shutting down MagenticOne API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.api_title,
        description="Multi-agent cryptocurrency analysis platform with real-time streaming",
        version=settings.api_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
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
    
    # WebSocket router for real-time streaming
    app.include_router(stream.router, tags=["WebSocket"])
    
    # REST API routers
    app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
    app.include_router(charts.router, prefix="/api/v1/charts", tags=["Charts"])
    app.include_router(settings_router.router, prefix="/api/v1", tags=["Settings"])
    
    # Static files for charts
    charts_dir = Path(settings.output_dir) / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/charts", StaticFiles(directory=str(charts_dir)), name="charts")

    # Static assets (e.g., chart libraries)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    return app


# Create app instance
app = create_app()


# Root endpoint for basic info
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "MagenticOne Crypto Analysis API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "websocket": "ws://localhost:8000/ws/stream",
        "ws_status": "/ws/status",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
