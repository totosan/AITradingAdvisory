"""
Crypto Financial Analysis Agent

This example demonstrates a specialized MagenticOne agent system for 
cryptocurrency analysis with technical indicators and chart generation.

Example Usage:
    python examples/crypto_analysis.py

Features:
    - Real-time crypto price monitoring
    - Technical indicator analysis (RSI, MACD, Bollinger Bands, SMA, EMA)
    - Candlestick chart generation
    - Market sentiment analysis
    - Multi-coin comparison
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor

from ollama_client import OllamaChatCompletionClient
from config import AppConfig
from crypto_tools import (
    get_crypto_price,
    get_historical_data,
    get_market_info,
    analyze_technical_indicators
)
from crypto_charts import create_crypto_chart

from rich.console import Console as RichConsole
from rich.panel import Panel
from rich.markdown import Markdown


async def create_crypto_analyst_team(config: AppConfig):
    """
    Create a specialized crypto analysis team.
    
    The team consists of:
    - Crypto Market Analyst: Expert in crypto markets and trends
    - Technical Analyst: Specializes in chart patterns and indicators
    - Coder: Generates analysis scripts and visualizations
    - Executor: Runs analysis code
    """
    console = RichConsole()
    
    # Initialize model client
    model_client = OllamaChatCompletionClient(
        model=config.ollama.model,
        base_url=config.ollama.base_url,
        temperature=config.ollama.temperature,
    )
    
    # Define available crypto tools
    crypto_tools = [
        get_crypto_price,
        get_historical_data,
        get_market_info,
        create_crypto_chart,
    ]
    
    # Crypto Market Analyst - focuses on market data and trends
    market_analyst = AssistantAgent(
        "CryptoMarketAnalyst",
        model_client=model_client,
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
        - get_crypto_price(): Get current price and basic stats
        - get_market_info(): Get detailed market information
        - get_historical_data(): Get price history for trend analysis
        
        Always provide clear, data-driven insights with specific numbers.""",
        description="Expert in crypto markets, trends, and fundamental analysis",
    )
    
    # Technical Analyst - focuses on charts and indicators
    technical_analyst = AssistantAgent(
        "TechnicalAnalyst",
        model_client=model_client,
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
        - create_crypto_chart(): Generate charts with indicators
        - get_historical_data(): Get price data for calculations
        
        Technical Analysis Guidelines:
        - RSI < 30 = Oversold (potential buy)
        - RSI > 70 = Overbought (potential sell)
        - MACD crossover = Trend change signal
        - Price above SMA = Bullish trend
        - Price near Bollinger Band edges = Potential reversal
        
        Always explain your technical findings in clear terms.""",
        description="Expert in technical analysis, charts, and indicators",
    )
    
    # Coder - generates analysis scripts and visualizations
    coder = AssistantAgent(
        "CryptoAnalysisCoder",
        model_client=model_client,
        system_message="""You are a Python developer specializing in crypto analysis tools.
        
        Your role is to:
        1. Write Python scripts for advanced crypto analysis
        2. Create custom calculations and data processing
        3. Generate comparative analysis across multiple coins
        4. Build reports and summaries
        5. Handle data processing and calculations
        
        When writing code:
        - Use the crypto_tools and crypto_charts modules
        - Save outputs to the 'outputs' directory
        - Include error handling
        - Make code clear and well-commented
        - Generate both numerical results and visualizations
        
        Available modules:
        - crypto_tools: get_crypto_price, get_historical_data, get_market_info
        - crypto_charts: create_crypto_chart
        
        Focus on creating actionable insights from the data.""",
        description="Python developer for crypto analysis scripts",
    )
    
    # Code executor
    output_dir = Path(config.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    code_executor = LocalCommandLineCodeExecutor(
        work_dir=str(output_dir / "code_execution"),
    )
    
    executor = CodeExecutorAgent(
        "Executor",
        code_executor=code_executor,
    )
    
    # Create the MagenticOne team
    team = MagenticOneGroupChat(
        participants=[market_analyst, technical_analyst, coder, executor],
        model_client=model_client,
        max_turns=config.max_turns,
        max_stalls=config.max_stalls,
    )
    
    console.print("✅ [green]Crypto Analysis Team initialized![/green]\n")
    
    return team


async def example_crypto_analysis():
    """Run example crypto analysis tasks."""
    console = RichConsole()
    
    # Display banner
    banner = """
# 🪙 Crypto Financial Analysis Agent
## Powered by MagenticOne

**Specialized Agents:**
- 📊 Crypto Market Analyst: Market data, trends, and fundamentals
- 📈 Technical Analyst: Charts, indicators, and trading signals  
- 👨‍💻 Analysis Coder: Custom scripts and visualizations
- 🖥️ Executor: Runs analysis code

**Capabilities:**
- Real-time price monitoring
- Technical indicator analysis (RSI, MACD, Bollinger Bands)
- Candlestick chart generation
- Multi-coin comparison
- Trading signal detection
"""
    console.print(Panel(Markdown(banner), border_style="yellow"))
    
    # Load configuration
    config = AppConfig.from_env()
    
    # Create the crypto analyst team
    console.print("\n[yellow]🚀 Initializing Crypto Analysis Team...[/yellow]\n")
    team = await create_crypto_analyst_team(config)
    
    # Example tasks
    tasks = [
        """Analyze Bitcoin (bitcoin) with the following:
        1. Get current price and market data
        2. Analyze technical indicators (RSI, MACD, SMA)
        3. Generate a candlestick chart with SMA, RSI, and MACD indicators for the last 30 days
        4. Provide a summary with bullish/bearish signals and trading recommendations""",
        
        """Compare Ethereum (ethereum) and Solana (solana):
        1. Get current prices and 24h/7d/30d changes for both
        2. Compare market cap, volume, and price performance
        3. Generate technical analysis charts for both (30 days)
        4. Recommend which one shows stronger technical signals""",
        
        """Analyze the top 3 cryptocurrencies:
        1. Get market data for Bitcoin, Ethereum, and BNB
        2. Compare their current market positions
        3. Identify which has the best technical setup
        4. Create a summary report with key metrics"""
    ]
    
    # Run the first example task
    console.print("\n" + "="*80)
    console.print(Panel(
        f"[bold cyan]Task:[/bold cyan]\n{tasks[0]}",
        border_style="cyan"
    ))
    console.print("="*80 + "\n")
    
    try:
        result = await Console(team.run_stream(task=tasks[0]))
        console.print("\n✅ [green]Analysis complete![/green]\n")
        console.print(Panel(str(result), title="Results", border_style="green"))
        
    except Exception as e:
        console.print(f"\n❌ [red]Error:[/red] {str(e)}")


async def interactive_crypto_mode():
    """Run interactive mode for custom crypto analysis."""
    console = RichConsole()
    
    banner = """
# 🪙 Interactive Crypto Analysis Mode

**Available Commands:**
- Analyze [coin]: Get full analysis with charts
- Price [coin]: Get current price
- Compare [coin1] vs [coin2]: Compare two cryptocurrencies
- Chart [coin] [days]: Generate chart for specified period
- exit/quit: Exit the program

**Popular Coins:**
bitcoin, ethereum, solana, cardano, polkadot, avalanche-2,
ripple, dogecoin, shiba-inu, chainlink, polygon, uniswap
"""
    console.print(Panel(Markdown(banner), border_style="yellow"))
    
    config = AppConfig.from_env()
    
    console.print("\n[yellow]🚀 Initializing Crypto Analysis Team...[/yellow]\n")
    team = await create_crypto_analyst_team(config)
    
    console.print("[cyan]Ready for analysis! Enter your command:[/cyan]\n")
    
    while True:
        try:
            task = console.input("\n[bold green]Crypto Analysis >[/bold green] ")
            
            if task.lower() in ['exit', 'quit', 'q']:
                console.print("\n👋 [yellow]Goodbye![/yellow]")
                break
            
            if not task.strip():
                continue
            
            console.print(f"\n[yellow]🔍 Analyzing...[/yellow]\n")
            
            result = await Console(team.run_stream(task=task))
            console.print("\n✅ [green]Analysis complete![/green]\n")
            
        except KeyboardInterrupt:
            console.print("\n\n👋 [yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"\n❌ [red]Error:[/red] {str(e)}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Crypto Financial Analysis Agent")
    parser.add_argument(
        "--mode",
        choices=["example", "interactive"],
        default="example",
        help="Run mode: 'example' for demo or 'interactive' for custom analysis"
    )
    
    args = parser.parse_args()
    
    if args.mode == "interactive":
        asyncio.run(interactive_crypto_mode())
    else:
        asyncio.run(example_crypto_analysis())
