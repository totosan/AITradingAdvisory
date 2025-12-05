"""
WebSocket event models.
"""
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel


# =============================================================================
# Server → Client Events
# =============================================================================

class AgentStepEvent(BaseModel):
    """Event when an agent starts or completes a step."""
    type: Literal["agent_step"] = "agent_step"
    agent: str
    emoji: str
    status: str  # "working", "completed", "error"
    message: Optional[str] = None
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
    interval: str  # Required by frontend
    timestamp: datetime


class FinalResultEvent(BaseModel):
    """Event with the final analysis result."""
    type: Literal["result"] = "result"
    content: str
    format: str = "markdown"
    agents_used: List[str]
    timestamp: datetime


class QuickResultEvent(BaseModel):
    """Event for quick/simple lookup results (no multi-agent processing)."""
    type: Literal["quick_result"] = "quick_result"
    content: str
    symbols: List[str]  # All symbols that were looked up
    tool_used: str
    intent_type: str
    confidence: float
    timestamp: datetime


class ErrorEvent(BaseModel):
    """Event when an error occurs."""
    type: Literal["error"] = "error"
    message: str
    details: Optional[str] = None
    recoverable: bool = True
    timestamp: datetime


class ContentFilterErrorEvent(BaseModel):
    """Event when Azure content filter is triggered."""
    type: Literal["content_filter_error"] = "content_filter_error"
    message: str
    triggered_prompt: str  # The prompt that triggered the filter
    filter_results: Optional[Dict[str, Any]] = None  # Detailed filter results
    filter_type: Optional[str] = None  # e.g., 'jailbreak', 'hate', 'violence'
    recoverable: bool = True
    timestamp: datetime


class ContentFilterRetryEvent(BaseModel):
    """Event when retrying after content filter - informs user of retry."""
    type: Literal["content_filter_retry"] = "content_filter_retry"
    message: str
    retry_attempt: int
    max_retries: int
    filter_type: Optional[str] = None
    timestamp: datetime


class ProgressEvent(BaseModel):
    """Event for progress updates."""
    type: Literal["progress"] = "progress"
    current_turn: int
    max_turns: int
    percentage: float
    timestamp: datetime


class StatusEvent(BaseModel):
    """General status event."""
    type: Literal["status"] = "status"
    status: str  # "connected", "processing", "idle", "disconnecting"
    message: Optional[str] = None
    timestamp: datetime


# =============================================================================
# Client → Server Messages
# =============================================================================

class ChatClientMessage(BaseModel):
    """Chat message from client."""
    type: Literal["chat"] = "chat"
    message: str
    conversation_id: Optional[str] = None


class CancelClientMessage(BaseModel):
    """Cancel request from client."""
    type: Literal["cancel"] = "cancel"


class SubscribeClientMessage(BaseModel):
    """Subscribe to real-time price updates."""
    type: Literal["subscribe"] = "subscribe"
    symbols: List[str]


class PingClientMessage(BaseModel):
    """Ping message for connection keepalive."""
    type: Literal["ping"] = "ping"


# =============================================================================
# Type Aliases for Event Union
# =============================================================================

ServerEvent = (
    AgentStepEvent | 
    ToolCallEvent | 
    ToolResultEvent | 
    ChartGeneratedEvent | 
    FinalResultEvent | 
    QuickResultEvent |
    ErrorEvent | 
    ContentFilterErrorEvent |
    ContentFilterRetryEvent |
    ProgressEvent |
    StatusEvent
)

ClientMessage = (
    ChatClientMessage |
    CancelClientMessage |
    SubscribeClientMessage |
    PingClientMessage
)
