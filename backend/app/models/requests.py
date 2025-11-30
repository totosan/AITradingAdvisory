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
    days: int = Field(default=30, ge=1, le=365)


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
    temperature: float = Field(default=0.7, ge=0, le=2)
