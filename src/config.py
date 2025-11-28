"""
Configuration module for MagenticOne Showcase
"""
import os
from typing import Optional, Literal
from dataclasses import dataclass


@dataclass
class AzureOpenAIConfig:
    """Configuration for Azure OpenAI."""
    api_key: str
    endpoint: str
    deployment: str = "gpt-4o"
    api_version: str = "2024-02-15-preview"
    
    @classmethod
    def from_env(cls) -> "AzureOpenAIConfig":
        """Create configuration from environment variables."""
        api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        
        if not api_key or not endpoint:
            raise ValueError(
                "Azure OpenAI credentials not found. Please set:\n"
                "  AZURE_OPENAI_API_KEY\n"
                "  AZURE_OPENAI_ENDPOINT\n"
                "in your .env file"
            )
        
        return cls(
            api_key=api_key,
            endpoint=endpoint,
            deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", cls.deployment),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", cls.api_version),
        )


@dataclass
class OllamaConfig:
    """Configuration for Ollama model."""
    base_url: str = "http://localhost:11434"
    model: str = "gpt-oss:20b"
    temperature: float = 0.7
    
    @classmethod
    def from_env(cls) -> "OllamaConfig":
        """Create configuration from environment variables."""
        return cls(
            base_url=os.getenv("OLLAMA_BASE_URL", cls.base_url),
            model=os.getenv("OLLAMA_MODEL", cls.model),
            temperature=float(os.getenv("OLLAMA_TEMPERATURE", str(cls.temperature))),
        )


@dataclass
class AppConfig:
    """Main application configuration."""
    llm_provider: Literal["azure", "ollama"] = "azure"
    azure_openai: Optional[AzureOpenAIConfig] = None
    ollama: Optional[OllamaConfig] = None
    output_dir: str = "outputs"
    max_turns: int = 20
    max_stalls: int = 3
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create configuration from environment variables."""
        provider = os.getenv("LLM_PROVIDER", "azure").lower()
        
        azure_config = None
        ollama_config = None
        
        if provider == "azure":
            azure_config = AzureOpenAIConfig.from_env()
        else:
            ollama_config = OllamaConfig.from_env()
        
        return cls(
            llm_provider=provider,  # type: ignore
            azure_openai=azure_config,
            ollama=ollama_config,
            output_dir=os.getenv("OUTPUT_DIR", cls.output_dir),
            max_turns=int(os.getenv("MAX_TURNS", str(cls.max_turns))),
            max_stalls=int(os.getenv("MAX_STALLS", str(cls.max_stalls))),
        )
