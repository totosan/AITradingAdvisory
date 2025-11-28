"""
MagenticOne Crypto Analysis Platform

A specialized multi-agent system for cryptocurrency market analysis,
technical indicators, chart generation, and trading signal detection.
"""
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

from rich.console import Console as RichConsole
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from rich import print as rprint

from ollama_client import OllamaChatCompletionClient
from config import AppConfig
from crypto_tools import (
    get_crypto_price,
    get_historical_data,
    get_market_info,
)
from crypto_charts import create_crypto_chart


class CryptoAnalysisPlatform:
    """
    Cryptocurrency Analysis Platform
    
    Multi-agent system for comprehensive crypto analysis:
    - Real-time price monitoring and market data
    - Technical indicator calculations (RSI, MACD, Bollinger Bands)
    - Professional candlestick chart generation
    - Trading signal detection and recommendations
    """
    
    def __init__(self, config: AppConfig):
        """Initialize the crypto analysis platform."""
        self.config = config
        self.console = RichConsole()
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize the model client based on provider
        if config.llm_provider == "azure":
            self.console.print(f"[cyan]Using Azure OpenAI: {config.azure_openai.deployment}[/cyan]")
            # Map deployment to a standard OpenAI model name for capabilities
            # Azure deployments can use custom names, so we assume gpt-4 capabilities
            model_name = "gpt-4" if "gpt-4" in config.azure_openai.deployment.lower() else "gpt-3.5-turbo"
            if "gpt-5" in config.azure_openai.deployment.lower():
                model_name = "gpt-4"  # GPT-5 uses same capabilities as GPT-4
            
            self.model_client = AzureOpenAIChatCompletionClient(
                azure_deployment=config.azure_openai.deployment,
                api_version=config.azure_openai.api_version,
                azure_endpoint=config.azure_openai.endpoint,
                api_key=config.azure_openai.api_key,
                model=model_name,
            )
        else:
            self.console.print(f"[cyan]Using Ollama: {config.ollama.model}[/cyan]")
            self.model_client = OllamaChatCompletionClient(
                model=config.ollama.model,
                base_url=config.ollama.base_url,
                temperature=config.ollama.temperature,
            )
        
    def display_banner(self):
        """Display the application banner."""
        banner = """
# 🪙 Crypto Analysis Platform
## Powered by MagenticOne Multi-Agent System

Specialized cryptocurrency analysis with:
- 📊 Real-time price monitoring & market data
- 📈 Technical indicators (RSI, MACD, Bollinger Bands, SMA, EMA)
- 📉 Professional candlestick chart generation
- 🎯 Trading signals & recommendations

**Specialized Agents:**
- 📊 Crypto Market Analyst: Prices, trends, fundamentals
- 📈 Technical Analyst: Charts, indicators, signals
- 👨‍💻 Analysis Coder: Custom scripts & comparisons
- 🖥️ Executor: Runs analysis & generates charts

**Data Source:** CoinGecko API (10,000+ cryptocurrencies)
"""
        self.console.print(Panel(Markdown(banner), border_style="cyan"))
    
    async def initialize_team(self) -> MagenticOneGroupChat:
        """
        Initialize the crypto analysis team with specialized agents.
        
        Returns:
            Configured MagenticOneGroupChat team with crypto specialists
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Initializing crypto analysis agents...", total=None)
            
            # Define crypto analysis tools
            crypto_tools = [
                get_crypto_price,
                get_historical_data,
                get_market_info,
                create_crypto_chart,
            ]
            
            # Crypto Market Analyst - focuses on market data and trends
            market_analyst = AssistantAgent(
                "CryptoMarketAnalyst",
                model_client=self.model_client,
                tools=crypto_tools,
                system_message="""You are a cryptocurrency market analyst with deep expertise in:
                - Crypto market dynamics and trends
                - Market cap analysis and ranking
                - Volume analysis and liquidity assessment
                - Price action and market sentiment
                - Fundamental analysis of cryptocurrencies
                
                Your role is to:
                1. Fetch and analyze current crypto prices and market data
                2. Track price changes over different time periods (24h, 7d, 30d)
                3. Analyze market capitalization and trading volume
                4. Identify market trends and potential opportunities
                5. Compare multiple cryptocurrencies
                
                Use the available tools to gather data:
                - get_crypto_price(symbol) - Get current price and basic stats
                - get_market_info(symbol) - Get detailed market information
                - get_historical_data(symbol, days) - Get price history for trend analysis
                
                Always provide clear, data-driven insights with specific numbers.""",
                description="Expert in crypto markets, trends, and fundamental analysis",
            )
            
            # Technical Analyst - focuses on charts and indicators
            technical_analyst = AssistantAgent(
                "TechnicalAnalyst",
                model_client=self.model_client,
                tools=crypto_tools,
                system_message="""You are a cryptocurrency technical analyst specializing in:
                - Chart pattern recognition
                - Technical indicator analysis (RSI, MACD, Bollinger Bands, Moving Averages)
                - Support and resistance levels
                - Trend analysis and momentum
                - Trading signals and entry/exit points
                
                Your role is to:
                1. Generate candlestick charts with technical indicators
                2. Calculate and interpret RSI, MACD, Bollinger Bands, SMA, EMA
                3. Identify overbought/oversold conditions
                4. Detect bullish/bearish signals
                5. Provide technical trading recommendations
                
                Use the available tools:
                - create_crypto_chart(symbol, days, indicators) - Generate charts with indicators
                - get_historical_data(symbol, days) - Get price data for calculations
                
                Technical Analysis Guidelines:
                - RSI < 30 = Oversold (potential buy)
                - RSI > 70 = Overbought (potential sell)
                - MACD crossover = Trend change signal
                - Price above SMA = Bullish trend
                - Price near Bollinger Band edges = Potential reversal
                
                Always explain your technical findings in clear terms.""",
                description="Expert in technical analysis, charts, and indicators",
            )
            
            coder = AssistantAgent(
                "CryptoAnalysisCoder",
                model_client=self.model_client,
                system_message="""You are a Python developer specializing in crypto analysis tools.
                
                Your role is to:
                1. Write Python scripts for advanced crypto analysis
                2. Create custom calculations and data processing
                3. Generate comparative analysis across multiple coins
                4. Build reports and summaries
                5. Handle data processing and calculations
                
                When writing code:
                - Import from crypto_tools: from crypto_tools import get_crypto_price, get_historical_data, get_market_info
                - Import from crypto_charts: from crypto_charts import create_crypto_chart
                - Use standard libraries: requests, json, pandas, numpy
                - Save outputs to the 'outputs' directory
                - Include error handling with try/except blocks
                - Make code clear and well-commented
                - Generate both numerical results and visualizations
                
                IMPORTANT: Do NOT import from modules that aren't installed. The available modules are:
                - crypto_tools (custom module with get_crypto_price, get_historical_data, get_market_info)
                - crypto_charts (custom module with create_crypto_chart)
                - Standard libraries: requests, json, pandas, numpy, datetime, pathlib
                
                Example import pattern:
                ```python
                from crypto_tools import get_crypto_price, get_historical_data
                import json
                ```
                
                Focus on creating actionable insights from the data.""",
                description="Python developer for crypto analysis scripts",
            )
            
            # Create code executor with local environment
            code_executor = LocalCommandLineCodeExecutor(
                work_dir=str(self.output_dir / "code_execution"),
            )
            
            executor = CodeExecutorAgent(
                "Executor",
                code_executor=code_executor,
            )
            
            # Create the crypto analysis team
            team = MagenticOneGroupChat(
                participants=[market_analyst, technical_analyst, coder, executor],
                model_client=self.model_client,
                max_turns=self.config.max_turns,
                max_stalls=self.config.max_stalls,
            )
            
        self.console.print("✅ [green]Crypto analysis team initialized successfully![/green]\n")
        return team
    
    async def run_task(self, task: str, save_output: bool = True) -> str:
        """
        Execute a task using the MagenticOne team.
        
        Args:
            task: The task description
            save_output: Whether to save the output to a file
            
        Returns:
            The task result
        """
        self.console.print(Panel(
            f"[bold cyan]Task:[/bold cyan]\n{task}",
            border_style="cyan"
        ))
        
        # Initialize team
        team = await self.initialize_team()
        
        # Execute task with streaming console output
        self.console.print("\n[yellow]🚀 Starting task execution...[/yellow]\n")
        
        try:
            result = await Console(team.run_stream(task=task))
            
            # Save output if requested
            if save_output:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = self.output_dir / f"task_output_{timestamp}.txt"
                
                with open(output_file, "w") as f:
                    f.write(f"Task: {task}\n\n")
                    f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
                    f.write("="*80 + "\n\n")
                    f.write(str(result))
                
                self.console.print(f"\n✅ [green]Output saved to:[/green] {output_file}")
            
            return str(result)
            
        except Exception as e:
            self.console.print(f"\n❌ [red]Error during task execution:[/red] {str(e)}")
            raise
    
    async def run_interactive_mode(self):
        """Run the crypto analysis platform in interactive mode."""
        self.display_banner()
        
        self.console.print("\n[cyan]Welcome to Crypto Analysis Interactive Mode![/cyan]")
        self.console.print("Analyze any cryptocurrency with technical indicators and charts.")
        self.console.print("\n[yellow]Popular coins:[/yellow] bitcoin, ethereum, solana, cardano, polkadot, avalanche-2")
        self.console.print("[yellow]Commands:[/yellow] 'Analyze [coin]', 'Compare [coin1] vs [coin2]', 'Chart [coin] [days]'")
        self.console.print("Type 'exit' or 'quit' to stop.\n")
        
        while True:
            try:
                # Get task from user
                task = self.console.input("\n[bold green]Crypto Analysis >[/bold green] ")
                
                if task.lower() in ['exit', 'quit', 'q']:
                    self.console.print("\n👋 [yellow]Goodbye![/yellow]")
                    break
                
                if not task.strip():
                    continue
                
                # Execute task
                await self.run_task(task)
                
            except KeyboardInterrupt:
                self.console.print("\n\n👋 [yellow]Interrupted by user. Goodbye![/yellow]")
                break
            except Exception as e:
                self.console.print(f"\n❌ [red]Error:[/red] {str(e)}")
                continue


async def main():
    """Main entry point for crypto analysis platform."""
    config = AppConfig.from_env()
    app = CryptoAnalysisPlatform(config)
    
    # Check command line arguments
    if len(sys.argv) > 1:
        # Run specific task from command line
        task = " ".join(sys.argv[1:])
        await app.run_task(task)
    else:
        # Run interactive mode
        await app.run_interactive_mode()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
