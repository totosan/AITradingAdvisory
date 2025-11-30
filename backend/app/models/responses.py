"""
Response models for API endpoints.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class ChatAcceptedResponse(BaseModel):
    """Response when a chat message is accepted."""
    conversation_id: str
    status: str = "accepted"
    message: Optional[str] = None


class ChatResponse(BaseModel):
    """Full response from a chat request (REST, non-streaming)."""
    conversation_id: str
    message: str
    agents_used: List[str]
    charts_generated: List[str] = []
    timestamp: datetime


class HistoryMessage(BaseModel):
    """A message in conversation history."""
    role: str  # 'user', 'assistant', 'agent'
    content: str
    agent_name: Optional[str] = None
    timestamp: datetime


class ConversationHistory(BaseModel):
    """Conversation history response."""
    conversation_id: str
    messages: List[HistoryMessage]
    created_at: datetime


class ChartResponse(BaseModel):
    """Response from chart generation."""
    chart_id: str
    file_path: str
    url: str
    symbol: str
    interval: str
    created_at: datetime


class ChartSummary(BaseModel):
    """Summary of a generated chart."""
    chart_id: str
    symbol: str
    interval: str
    url: str
    created_at: datetime


class ExchangeStatus(BaseModel):
    """Exchange connection status."""
    configured: bool
    exchange: str = "bitget"
    connected: bool = False
    last_checked: Optional[datetime] = None


class LLMConfigResponse(BaseModel):
    """Current LLM configuration."""
    provider: str
    model: str
    base_url: Optional[str] = None
    connected: bool


class StatusResponse(BaseModel):
    """Generic status response."""
    status: str  # 'success', 'warning', 'error'
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
