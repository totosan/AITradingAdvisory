"""
Charts REST API routes.

Provides endpoints for generating and managing TradingView-style charts.
All routes require authentication - charts are scoped to users.
"""
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging
import json

from fastapi import APIRouter, HTTPException, Query, Depends

from app.models.requests import ChartRequest
from app.models.responses import ChartResponse, ChartSummary
from app.models.database import User
from app.core.config import get_settings
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory chart registry keyed by user_id -> chart_id
# Structure: {user_id: {chart_id: chart_data}}
# Replace with database in production (Phase 6.2)
user_chart_registry: dict = {}


@router.post("/", response_model=ChartResponse)
async def generate_chart(
    request: ChartRequest,
    user: User = Depends(get_current_user),
):
    """
    Generate a TradingView-style chart.
    
    Supports various indicators: rsi, macd, bollinger, sma, ema, volume
    Chart is owned by the authenticated user.
    """
    user_id = str(user.id)
    settings = get_settings()
    chart_id = str(uuid.uuid4())[:8]
    
    # Initialize user's chart storage if new
    if user_id not in user_chart_registry:
        user_chart_registry[user_id] = {}
    
    try:
        # Import chart generation tools
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))
        
        from tradingview_tools import generate_tradingview_chart
        
        # Generate the chart
        result = generate_tradingview_chart(
            symbol=request.symbol,
            interval=request.interval,
            indicators=",".join(request.indicators),
            theme=request.theme,
            title=f"{request.symbol} Chart",
        )
        
        # Parse result (it's a JSON string)
        if isinstance(result, str):
            try:
                chart_data = json.loads(result)
            except json.JSONDecodeError:
                chart_data = {"file": result}
        else:
            chart_data = result
        
        file_path = chart_data.get("file", chart_data.get("path", ""))
        
        if not file_path:
            raise HTTPException(status_code=500, detail="Chart generation failed - no file path")
        
        # Extract filename for URL
        filename = Path(file_path).name
        url = f"/charts/{filename}"
        
        # Register the chart
        chart_info = ChartResponse(
            chart_id=chart_id,
            file_path=file_path,
            url=url,
            symbol=request.symbol,
            interval=request.interval,
            created_at=datetime.now(),
        )
        
        user_chart_registry[user_id][chart_id] = chart_info.model_dump(mode='json')
        
        return chart_info
        
    except ImportError as e:
        logger.error(f"Failed to import chart tools: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Chart generation not available: {str(e)}"
        )
    except Exception as e:
        logger.exception("Chart generation failed")
        raise HTTPException(
            status_code=500,
            detail=f"Chart generation failed: {str(e)}"
        )


@router.get("/", response_model=List[ChartSummary])
async def list_charts(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of charts"),
    user: User = Depends(get_current_user),
):
    """
    List generated charts for the authenticated user.
    """
    user_id = str(user.id)
    
    if user_id not in user_chart_registry:
        return []
    
    charts = list(user_chart_registry[user_id].values())
    
    # Filter by symbol if provided
    if symbol:
        symbol_upper = symbol.upper()
        charts = [c for c in charts if c.get("symbol", "").upper() == symbol_upper]
    
    # Sort by created_at descending
    charts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # Apply limit
    charts = charts[:limit]
    
    return [
        ChartSummary(
            chart_id=c["chart_id"],
            symbol=c["symbol"],
            interval=c["interval"],
            url=c["url"],
            created_at=datetime.fromisoformat(c["created_at"]) if isinstance(c["created_at"], str) else c["created_at"],
        )
        for c in charts
    ]


@router.get("/{chart_id}", response_model=ChartResponse)
async def get_chart(
    chart_id: str,
    user: User = Depends(get_current_user),
):
    """
    Get chart details by ID. Only returns charts owned by the authenticated user.
    """
    user_id = str(user.id)
    
    if user_id not in user_chart_registry or chart_id not in user_chart_registry[user_id]:
        raise HTTPException(status_code=404, detail="Chart not found")
    
    chart_data = user_chart_registry[user_id][chart_id]
    return ChartResponse(
        chart_id=chart_data["chart_id"],
        file_path=chart_data["file_path"],
        url=chart_data["url"],
        symbol=chart_data["symbol"],
        interval=chart_data["interval"],
        created_at=datetime.fromisoformat(chart_data["created_at"]) if isinstance(chart_data["created_at"], str) else chart_data["created_at"],
    )


@router.delete("/{chart_id}")
async def delete_chart(
    chart_id: str,
    user: User = Depends(get_current_user),
):
    """
    Delete a chart owned by the authenticated user.
    """
    user_id = str(user.id)
    
    if user_id not in user_chart_registry or chart_id not in user_chart_registry[user_id]:
        raise HTTPException(status_code=404, detail="Chart not found")
    
    chart_data = user_chart_registry[user_id].pop(chart_id)
    
    # Try to delete the file
    try:
        file_path = Path(chart_data["file_path"])
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        logger.warning(f"Failed to delete chart file: {e}")
    
    return {"status": "deleted", "chart_id": chart_id}


@router.post("/multi-timeframe", response_model=ChartResponse)
async def generate_multi_timeframe_dashboard(
    symbol: str = Query(..., description="Trading pair symbol (e.g., BTCUSDT)"),
    timeframes: str = Query("15m,1H,4H,1D", description="Comma-separated timeframes"),
    user: User = Depends(get_current_user),
):
    """
    Generate a multi-timeframe analysis dashboard.
    Chart is owned by the authenticated user.
    """
    user_id = str(user.id)
    settings = get_settings()
    chart_id = str(uuid.uuid4())[:8]
    
    # Initialize user's chart storage if new
    if user_id not in user_chart_registry:
        user_chart_registry[user_id] = {}
    
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))
        
        from tradingview_tools import generate_multi_timeframe_dashboard as gen_mtf
        
        result = gen_mtf(symbol=symbol, timeframes=timeframes)
        
        if isinstance(result, str):
            try:
                chart_data = json.loads(result)
            except json.JSONDecodeError:
                chart_data = {"file": result}
        else:
            chart_data = result
        
        file_path = chart_data.get("file", chart_data.get("path", ""))
        filename = Path(file_path).name if file_path else f"mtf_{symbol}_{chart_id}.html"
        url = f"/charts/{filename}"
        
        chart_info = ChartResponse(
            chart_id=chart_id,
            file_path=file_path,
            url=url,
            symbol=symbol,
            interval=timeframes,
            created_at=datetime.now(),
        )
        
        user_chart_registry[user_id][chart_id] = chart_info.model_dump(mode='json')
        
        return chart_info
        
    except Exception as e:
        logger.exception("Multi-timeframe dashboard generation failed")
        raise HTTPException(
            status_code=500,
            detail=f"Dashboard generation failed: {str(e)}"
        )


@router.post("/alerts-dashboard", response_model=ChartResponse)
async def generate_alerts_dashboard(
    symbol: str = Query(..., description="Trading pair symbol (e.g., BTCUSDT)"),
    user: User = Depends(get_current_user),
):
    """
    Generate a smart alerts dashboard with AI-powered trading signals.
    Chart is owned by the authenticated user.
    """
    user_id = str(user.id)
    settings = get_settings()
    chart_id = str(uuid.uuid4())[:8]
    
    # Initialize user's chart storage if new
    if user_id not in user_chart_registry:
        user_chart_registry[user_id] = {}
    
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))
        
        from smart_alerts import generate_smart_alerts_dashboard
        
        result = generate_smart_alerts_dashboard(symbol=symbol)
        
        if isinstance(result, str):
            try:
                chart_data = json.loads(result)
            except json.JSONDecodeError:
                chart_data = {"file": result}
        else:
            chart_data = result
        
        file_path = chart_data.get("file", chart_data.get("path", ""))
        filename = Path(file_path).name if file_path else f"alerts_{symbol}_{chart_id}.html"
        url = f"/charts/{filename}"
        
        chart_info = ChartResponse(
            chart_id=chart_id,
            file_path=file_path,
            url=url,
            symbol=symbol,
            interval="alerts",
            created_at=datetime.now(),
        )
        
        user_chart_registry[user_id][chart_id] = chart_info.model_dump(mode='json')
        
        return chart_info
        
    except Exception as e:
        logger.exception("Alerts dashboard generation failed")
        raise HTTPException(
            status_code=500,
            detail=f"Alerts dashboard generation failed: {str(e)}"
        )
