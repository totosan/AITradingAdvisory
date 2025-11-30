"""
Application configuration using Pydantic Settings.

Environment variables are loaded from .env file or environment.
"""
from functools import lru_cache
from typing import List, Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # ==========================================================================
    # API Settings
    # ==========================================================================
    api_title: str = "MagenticOne Crypto Analysis API"
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
    
    # ==========================================================================
    # Agent Configuration
    # ==========================================================================
    max_turns: int = 20
    max_stalls: int = 3
    
    # ==========================================================================
    # Storage
    # ==========================================================================
    output_dir: str = "outputs"
    secrets_dir: str = "/app/data"
    
    class Config:
        env_file = ".env"
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
