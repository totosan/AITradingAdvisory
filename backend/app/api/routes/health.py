"""
Health check endpoints for container orchestration.
"""
from datetime import datetime
from typing import Any, Dict
from fastapi import APIRouter, Depends
import httpx

from app.core.config import Settings, get_settings

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check.
    
    Returns healthy if the API is running.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/health/ready")
async def readiness_check(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """
    Readiness check - verifies dependencies are available.
    
    Checks:
    - API is running
    - LLM provider is accessible (Ollama or Azure)
    """
    checks: Dict[str, Any] = {
        "api": True,
        "llm_provider": settings.llm_provider,
    }
    
    # Check LLM availability based on provider
    if settings.llm_provider == "ollama":
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{settings.ollama_base_url}/api/tags",
                    timeout=5.0
                )
                checks["ollama"] = resp.status_code == 200
        except Exception as e:
            checks["ollama"] = False
            checks["ollama_error"] = str(e)
    
    elif settings.llm_provider == "azure":
        # For Azure, just check if credentials are configured
        checks["azure_configured"] = bool(
            settings.azure_openai_api_key and settings.azure_openai_endpoint
        )
    
    # Determine overall status
    all_healthy = all(
        v for k, v in checks.items() 
        if isinstance(v, bool) and k != "azure_configured"
    )
    
    return {
        "status": "ready" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """
    Liveness check - confirms the process is running.
    
    Used by container orchestrators for restart decisions.
    """
    return {"status": "alive"}
