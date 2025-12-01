"""
Configuration module for MagenticOne Showcase
"""
import os
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class BitgetConfig:
    """Configuration for Bitget API."""
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None
    timeout: int = 10
    
    @classmethod
    def from_env(cls) -> "BitgetConfig":
        """Create configuration from environment variables."""
        return cls(
            api_key=os.getenv("BITGET_API_KEY"),
            api_secret=os.getenv("BITGET_API_SECRET"),
            passphrase=os.getenv("BITGET_PASSPHRASE"),
            timeout=int(os.getenv("BITGET_TIMEOUT", "10")),
        )
    
    @property
    def is_configured(self) -> bool:
        """Check if all required credentials are set."""
        return all([self.api_key, self.api_secret, self.passphrase])


@dataclass
class ExchangeConfig:
    """Configuration for exchange providers."""
    # Default provider to use: 'bitget' or 'coingecko'
    default_provider: str = "coingecko"
    # Enable Bitget provider
    enable_bitget: bool = True
    # Enable CoinGecko provider (for comparison/fallback)
    enable_coingecko: bool = True
    # Bitget-specific config
    bitget: Optional[BitgetConfig] = None
    
    @classmethod
    def from_env(cls) -> "ExchangeConfig":
        """Create configuration from environment variables."""
        return cls(
            default_provider=os.getenv("EXCHANGE_DEFAULT_PROVIDER", "coingecko"),
            enable_bitget=os.getenv("EXCHANGE_ENABLE_BITGET", "true").lower() == "true",
            enable_coingecko=os.getenv("EXCHANGE_ENABLE_COINGECKO", "true").lower() == "true",
            bitget=BitgetConfig.from_env(),
        )


@dataclass
class AzureOpenAIConfig:
    """Configuration for Azure OpenAI."""
    api_key: str
    endpoint: str
    deployment: str = "gpt-4o"
    model_name: str = "gpt-4o"  # The actual model name for token estimation
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
        
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", cls.deployment)
        # Model name defaults to deployment name, but can be overridden
        model_name = os.getenv("AZURE_OPENAI_MODEL_NAME", deployment)
        
        return cls(
            api_key=api_key,
            endpoint=endpoint,
            deployment=deployment,
            model_name=model_name,
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", cls.api_version),
        )


@dataclass
class AppConfig:
    """Main application configuration."""
    azure_openai: Optional[AzureOpenAIConfig] = None
    exchange: Optional[ExchangeConfig] = None
    output_dir: str = "outputs"
    max_turns: int = 20
    max_stalls: int = 3
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create configuration from environment variables."""
        return cls(
            azure_openai=AzureOpenAIConfig.from_env(),
            exchange=ExchangeConfig.from_env(),
            output_dir=os.getenv("OUTPUT_DIR", cls.output_dir),
            max_turns=int(os.getenv("MAX_TURNS", str(cls.max_turns))),
            max_stalls=int(os.getenv("MAX_STALLS", str(cls.max_stalls))),
        )


