"""
Application configuration using Pydantic Settings.

Environment variables are loaded from .env file or environment.
"""
from functools import lru_cache
from pathlib import Path
from typing import List, Literal, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

# Compute project root at module load time
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.absolute()


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # ==========================================================================
    # API Settings
    # ==========================================================================
    api_title: str = "AITradingAdvisory Crypto Analysis API"
    api_version: str = "1.0.0"
    debug: bool = False
    
    # CORS - comma separated in env, parsed to list
    cors_origins: List[str] = [
        "http://localhost:3000", 
        "http://localhost:5173",
        "http://localhost:5174",
        "https://*.app.github.dev",
        "https://*.github.dev",
        "*"  # Allow all for development
    ]
    
    # ==========================================================================
    # LLM Provider Configuration
    # ==========================================================================
    llm_provider: Literal["ollama", "azure"] = "ollama"
    
    # Ollama settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gpt-oss:20b"
    ollama_temperature: float = 0.7
    
    # Azure OpenAI settings
    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-02-15-preview"
    azure_openai_model_name: Optional[str] = None
    
    # ==========================================================================
    # Exchange Provider Configuration
    # ==========================================================================
    exchange_default_provider: str = "coingecko"
    exchange_enable_bitget: bool = True
    exchange_enable_coingecko: bool = True
    
    # Bitget API Configuration
    bitget_api_key: Optional[str] = None
    bitget_api_secret: Optional[str] = None
    bitget_passphrase: Optional[str] = None
    bitget_timeout: int = 10
    
    # ==========================================================================
    # Agent Configuration
    # ==========================================================================
    max_turns: int = 20
    max_stalls: int = 3
    
    # ==========================================================================
    # Storage
    # ==========================================================================
    # Use /app/outputs in Docker, project root outputs/ for local dev
    # Note: Must use absolute paths to avoid CWD issues when running from different directories
    output_dir: str = Field(default="/app/outputs" if Path("/app").exists() else str(_PROJECT_ROOT / "outputs"))
    # Use /app/data in Docker, project data/ dir for local development
    secrets_dir: str = Field(default="/app/data" if Path("/app/data").exists() else str(_PROJECT_ROOT / "data"))
    
    class Config:
        # Look for .env in project root (3 levels up from this file)
        env_file = Path(__file__).parent.parent.parent.parent / ".env"
        env_file_encoding = "utf-8"
        # Allow comma-separated lists for CORS origins
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            if field_name == "cors_origins":
                return [x.strip() for x in raw_val.split(",")]
            return raw_val


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
