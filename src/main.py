"""
MagenticOne Crypto Analysis Platform

A specialized multi-agent system for cryptocurrency market analysis,
technical indicators, chart generation, and trading signal detection.
"""
import asyncio
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.ui import Console
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import (
    AgentEvent,
    ChatMessage,
    TextMessage,
    ThoughtEvent,
    ToolCallRequestEvent,
    ToolCallExecutionEvent,
    HandoffMessage,
    StopMessage,
    ToolCallSummaryMessage,
    ModelClientStreamingChunkEvent,
)
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

from rich.console import Console as RichConsole
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from rich import print as rprint

from config import AppConfig
from crypto_tools import (
    get_crypto_price,
    get_historical_data,
    get_market_info,
)
from crypto_charts import create_crypto_chart
from exchange_tools import (
    get_realtime_price,
    get_price_comparison,
    get_orderbook_depth,
    get_ohlcv_data,
    get_recent_market_trades,
    get_futures_data,
    get_futures_candles,
    get_account_balance,
    check_exchange_status,
)
from report_tools import (
    save_markdown_report,
    create_analysis_report,
    create_comparison_report,
    create_custom_indicator_report,
)
from indicator_registry import (
    save_custom_indicator,
    list_custom_indicators,
    get_custom_indicator,
    delete_custom_indicator,
    get_indicator_code_for_execution,
)
from tradingview_tools import (
    generate_tradingview_chart,
    create_ai_annotated_chart,
    generate_multi_timeframe_dashboard,
    generate_strategy_backtest_chart,
)
from tradingview_udf_server import (
    start_udf_server,
    stop_udf_server,
    get_udf_server_status,
    generate_live_chart_with_data,
)
from smart_alerts import (
    generate_smart_alerts_dashboard,
    create_trade_idea_alert,
)


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
        
        # Conversation history for multi-turn interactions
        self.conversation_history: List[Dict[str, str]] = []
        self.team = None  # Persistent team for conversation mode
        
        # Initialize the Azure OpenAI model client
        self.console.print(f"[cyan]Using Azure OpenAI: {config.azure_openai.deployment}[/cyan]")
        
        # Model info for GPT-5 or other new models not yet in autogen's registry
        model_info = {
            "vision": True,
            "function_calling": True,
            "json_output": True,
            "structured_output": True,
            "family": "gpt-5",
        }
        
        self.model_client = AzureOpenAIChatCompletionClient(
            azure_deployment=config.azure_openai.deployment,
            api_version=config.azure_openai.api_version,
            azure_endpoint=config.azure_openai.endpoint,
            api_key=config.azure_openai.api_key,
            model=config.azure_openai.model_name,
            model_info=model_info,
        )
    
    async def _process_stream_minimal(self, stream) -> TaskResult:
        """
        Process the agent stream with minimal output.
        
        Only displays:
        - Agent names when they start working (thinking steps)
        - The final answer
        
        Args:
            stream: The async stream from team.run_stream()
            
        Returns:
            The TaskResult from the stream
        """
        last_agent = None
        final_result = None
        
        async for message in stream:
            # Track TaskResult
            if isinstance(message, TaskResult):
                final_result = message
                continue
            
            # Get the source/agent name
            source = getattr(message, 'source', None)
            
            # When a new agent starts, show their name
            if source and source != last_agent:
                # Show agent step
                agent_emoji = {
                    'CryptoMarketAnalyst': '📊',
                    'TechnicalAnalyst': '📈', 
                    'CryptoAnalysisCoder': '👨‍💻',
                    'ReportWriter': '📝',
                    'ChartingAgent': '📉',
                    'Executor': '🖥️',
                }.get(source, '🤖')
                
                self.console.print(f"\n{agent_emoji} [bold cyan]{source}[/bold cyan] is working...")
                last_agent = source
            
            # Show tool calls briefly
            if isinstance(message, ToolCallRequestEvent):
                for call in message.content:
                    tool_name = call.name if hasattr(call, 'name') else str(call)
                    self.console.print(f"   ↳ Calling: [dim]{tool_name}[/dim]")
        
        # Display final answer
        if final_result and final_result.messages:
            # Find the last text message as the answer
            for msg in reversed(final_result.messages):
                if isinstance(msg, (TextMessage, StopMessage)):
                    content = msg.content if hasattr(msg, 'content') else str(msg)
                    if content and not content.startswith("TERMINATE"):
                        self.console.print("\n" + "─" * 60)
                        self.console.print("[bold green]✅ Answer:[/bold green]\n")
                        # Use Markdown rendering for nice formatting
                        self.console.print(Markdown(content))
                        break
        
        return final_result
        
    def display_banner(self):
        """Display the application banner."""
        banner = """
# 🪙 Crypto Analysis Platform
## Powered by MagenticOne Multi-Agent System

Specialized cryptocurrency analysis with:
- 📊 Real-time price monitoring & market data
- 📈 Technical indicators (RSI, MACD, Bollinger Bands, SMA, EMA)
- 📉 Professional TradingView-style charts & multi-timeframe dashboards
- 🎯 Trading signals & recommendations
- 💹 Futures trading data & account management
- 🧪 **Custom indicator creation & backtesting**
- 📝 **Professional Markdown report generation**
- 💾 **Persistent indicator registry** - Save & reuse indicators across sessions
- 🖼️ **TradingView Charting** - Interactive charts with live data

**Specialized Agents:**
- 📊 Crypto Market Analyst: Prices, trends, custom indicator ideas
- 📈 Technical Analyst: Charts, indicators, signal design & evaluation
- 📉 **Charting Agent**: TradingView charts, multi-timeframe dashboards, backtest visualizations
- 👨‍💻 Analysis Coder: Implements indicators, backtests strategies
- 📝 Report Writer: Creates professional Markdown reports
- 🖥️ Executor: Runs analysis & generates charts

**Data Sources:**
- 🔶 **Bitget Exchange** - Real-time spot & futures data, order books, account balances
- 🦎 **CoinGecko API** - 10,000+ cryptocurrencies, market data, historical prices

💬 **Conversation Mode** - Ask follow-up questions! Agents remember context.
💡 *Try: "Create a multi-timeframe dashboard for BTC" or "Generate an annotated chart with buy signals"*
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
            
            # Define crypto analysis tools (CoinGecko-based)
            coingecko_tools = [
                get_crypto_price,
                get_historical_data,
                get_market_info,
                create_crypto_chart,
            ]
            
            # Define exchange tools (Bitget + multi-exchange)
            exchange_tools = [
                get_realtime_price,
                get_price_comparison,
                get_orderbook_depth,
                get_ohlcv_data,
                get_recent_market_trades,
                get_futures_data,
                get_futures_candles,
                get_account_balance,
                check_exchange_status,
            ]
            
            # Define report generation tools
            report_tools = [
                save_markdown_report,
                create_analysis_report,
                create_comparison_report,
                create_custom_indicator_report,
            ]
            
            # Define indicator registry tools (for persistent custom indicators)
            indicator_tools = [
                save_custom_indicator,
                list_custom_indicators,
                get_custom_indicator,
                delete_custom_indicator,
                get_indicator_code_for_execution,
            ]
            
            # Define TradingView charting tools
            tradingview_tools = [
                generate_tradingview_chart,
                create_ai_annotated_chart,
                generate_multi_timeframe_dashboard,
                generate_strategy_backtest_chart,
                start_udf_server,
                stop_udf_server,
                get_udf_server_status,
                generate_live_chart_with_data,
                generate_smart_alerts_dashboard,
                create_trade_idea_alert,
            ]
            
            # All tools combined
            all_crypto_tools = coingecko_tools + exchange_tools
            
            # Crypto Market Analyst - focuses on market data and trends
            market_analyst = AssistantAgent(
                "CryptoMarketAnalyst",
                model_client=self.model_client,
                tools=all_crypto_tools,
                system_message="""You are a cryptocurrency market analyst with deep expertise in:
                - Crypto market dynamics and trends
                - Market cap analysis and ranking
                - Volume analysis and liquidity assessment
                - Price action and market sentiment
                - Fundamental analysis of cryptocurrencies
                - Real-time exchange data analysis
                - **Identifying when custom indicators are needed**
                
                Your role is to:
                1. Fetch and analyze current crypto prices from multiple sources
                2. Track price changes over different time periods (24h, 7d, 30d)
                3. Analyze market capitalization and trading volume
                4. Identify market trends and potential opportunities
                5. Compare prices across exchanges (Bitget vs CoinGecko)
                6. Monitor order book depth and liquidity
                7. **Suggest custom indicator ideas** when standard metrics fall short
                8. **Validate indicator effectiveness** with market context
                
                **WHEN TO SUGGEST CUSTOM INDICATORS:**
                - Standard RSI/MACD not capturing crypto-specific dynamics
                - Need to combine on-chain/futures data with price action
                - Market conditions are unusual (high funding, extreme volume)
                - Looking for edge in specific market regimes
                
                **CUSTOM INDICATOR IDEAS YOU CAN PROPOSE:**
                - Funding Rate Momentum: Track funding rate changes as sentiment
                - Volume-Weighted Momentum: Weight price moves by volume significance
                - Open Interest Divergence: Price vs OI relationship for reversals
                - Orderbook Imbalance Score: Bid/ask ratio for short-term direction
                - Multi-timeframe Trend Alignment: Combine 1H, 4H, 1D signals
                - Volatility Regime Detector: High/low vol state identification
                
                Work with TechnicalAnalyst to design indicators and CryptoAnalysisCoder to implement them!
                
                **DATA SOURCES AVAILABLE:**
                
                🦎 CoinGecko Tools (broad market data, 10,000+ coins):
                - get_crypto_price(symbol) - Get current price (use coin IDs like 'bitcoin', 'ethereum')
                - get_market_info(symbol) - Get detailed market information
                - get_historical_data(symbol, days) - Get price history for trend analysis
                
                🔶 Bitget Exchange Tools (real-time trading data):
                - get_realtime_price(symbol, provider) - Real-time price (use pairs like 'BTCUSDT', 'ETHUSDT')
                - get_price_comparison(symbol) - Compare prices across Bitget and CoinGecko
                - get_orderbook_depth(symbol, levels) - Order book with bid/ask levels
                - get_recent_market_trades(symbol, limit) - Recent trade history
                - check_exchange_status() - Check which exchanges are connected
                
                **SYMBOL FORMATS:**
                - CoinGecko: lowercase coin IDs → 'bitcoin', 'ethereum', 'solana', 'sui'
                - Bitget: trading pairs with USDT → 'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'SUIUSDT'
                
                Always provide clear, data-driven insights with specific numbers.
                When standard analysis is insufficient, propose custom indicator concepts!""",
                description="Expert in crypto markets, trends, fundamental analysis, and custom indicator design",
            )
            
            # Technical Analyst - focuses on charts and indicators
            technical_analyst = AssistantAgent(
                "TechnicalAnalyst",
                model_client=self.model_client,
                tools=all_crypto_tools + indicator_tools,
                system_message="""You are a cryptocurrency technical analyst specializing in:
                - Chart pattern recognition
                - Technical indicator analysis (RSI, MACD, Bollinger Bands, Moving Averages)
                - Support and resistance levels
                - Trend analysis and momentum
                - Trading signals and entry/exit points
                - Futures market analysis
                - **CUSTOM INDICATOR DESIGN** - Create new indicators when standard ones are insufficient
                - **REUSING SAVED INDICATORS** - Check the indicator registry for existing tools
                
                Your role is to:
                1. Generate candlestick charts with technical indicators
                2. Calculate and interpret RSI, MACD, Bollinger Bands, SMA, EMA
                3. Identify overbought/oversold conditions
                4. Detect bullish/bearish signals
                5. Provide technical trading recommendations
                6. Analyze futures data including funding rates and open interest
                7. **CHECK FOR EXISTING INDICATORS** in the registry before designing new ones
                8. **DESIGN CUSTOM INDICATORS** when needed for specific analysis goals
                9. **EVALUATE INDICATOR PERFORMANCE** using backtesting and signal accuracy
                
                **INDICATOR REGISTRY - CHECK FIRST!**
                Before designing a new indicator, ALWAYS check if one already exists:
                - list_custom_indicators() - See all saved indicators
                - list_custom_indicators(category="momentum") - Filter by category
                - list_custom_indicators(search="funding") - Search by keyword
                - get_custom_indicator(indicator_id) - Get full details and code
                
                **CUSTOM INDICATOR DESIGN:**
                When standard indicators don't capture what you need, design new ones:
                - Combine multiple signals (e.g., RSI + Volume + Funding Rate)
                - Create composite scores (e.g., "Momentum Health Score")
                - Build crypto-specific indicators (e.g., "Whale Accumulation Index")
                - Develop market regime detectors (trending vs ranging)
                
                Ask the CryptoAnalysisCoder to implement and SAVE your indicator designs!
                
                **INDICATOR EVALUATION CRITERIA:**
                - Signal accuracy: % of correct buy/sell predictions
                - Sharpe ratio of signals vs buy-and-hold
                - Win rate and risk-reward ratio
                - False positive/negative rates
                - Performance across different market conditions
                
                **DATA SOURCES AVAILABLE:**
                
                🦎 CoinGecko Tools (historical data, charting):
                - create_crypto_chart(symbol, days, indicators) - Generate charts (coin IDs: 'bitcoin', 'ethereum')
                - get_historical_data(symbol, days) - Get price data for calculations
                
                🔶 Bitget Exchange Tools (real-time OHLCV, futures):
                - get_ohlcv_data(symbol, interval, limit) - Candlestick data (pairs: 'BTCUSDT', 'ETHUSDT')
                  Intervals: '1m', '5m', '15m', '1H', '4H', '1D', '1W'
                - get_futures_data(symbol) - Futures info: funding rate, open interest, mark price
                - get_futures_candles(symbol, interval, limit) - Futures OHLCV data
                - get_orderbook_depth(symbol, levels) - Order book for support/resistance
                
                **SYMBOL FORMATS:**
                - CoinGecko: lowercase coin IDs → 'bitcoin', 'ethereum', 'solana'
                - Bitget Spot: pairs → 'BTCUSDT', 'ETHUSDT', 'SOLUSDT'
                - Bitget Futures: same pairs → 'BTCUSDT', 'ETHUSDT'
                
                Technical Analysis Guidelines:
                - RSI < 30 = Oversold (potential buy)
                - RSI > 70 = Overbought (potential sell)
                - MACD crossover = Trend change signal
                - Price above SMA = Bullish trend
                - Price near Bollinger Band edges = Potential reversal
                - Positive funding rate = Longs pay shorts (bullish sentiment)
                - High open interest = Strong trend conviction
                
                Always explain your technical findings in clear terms.
                When proposing custom indicators, explain the logic and expected edge.""",
                description="Expert in technical analysis, charts, indicators, futures, and custom indicator design",
            )
            
            coder = AssistantAgent(
                "CryptoAnalysisCoder",
                model_client=self.model_client,
                tools=indicator_tools,
                system_message="""You are a Python developer specializing in crypto analysis tools and **quantitative trading systems**.
                
                Your role is to:
                1. Write Python scripts for advanced crypto analysis
                2. Create custom calculations and data processing
                3. Generate comparative analysis across multiple coins
                4. Build reports and summaries
                5. Handle data processing and calculations
                6. Fetch and process exchange data from Bitget and CoinGecko
                7. **IMPLEMENT CUSTOM INDICATORS** designed by the TechnicalAnalyst
                8. **BACKTEST AND EVALUATE** indicator/strategy performance
                9. **SAVE INDICATORS** to the registry for reuse across sessions
                10. **LOAD EXISTING INDICATORS** from the registry when available
                
                **INDICATOR REGISTRY - PERSISTENT STORAGE:**
                You have access to a persistent indicator registry. ALWAYS check for existing
                indicators before creating new ones, and ALWAYS save new indicators for reuse!
                
                📚 **Registry Tools:**
                - list_custom_indicators(category, search) - List all saved indicators
                - get_custom_indicator(indicator_id) - Get full details and code for an indicator
                - save_custom_indicator(...) - Save a new indicator to the registry
                - get_indicator_code_for_execution(indicator_id) - Get executable code
                - delete_custom_indicator(indicator_id, confirm) - Remove an indicator
                
                **WORKFLOW FOR CUSTOM INDICATORS:**
                1. FIRST: Check if a similar indicator exists with list_custom_indicators()
                2. If exists: Load it with get_custom_indicator() and adapt if needed
                3. If new: Create the indicator, test it, then save with save_custom_indicator()
                4. ALWAYS save working indicators so they can be reused in future sessions!
                
                **WHEN SAVING INDICATORS, INCLUDE:**
                - Clear function name and description
                - All parameters with defaults
                - Usage example showing how to call it
                - Performance notes from backtesting
                - Appropriate category and tags for searchability
                
                **CUSTOM INDICATOR IMPLEMENTATION:**
                When the TechnicalAnalyst designs a new indicator, implement it with:
                - Clear function signature with type hints
                - Configurable parameters (periods, thresholds, etc.)
                - NaN handling for warmup periods
                - Efficient pandas/numpy vectorized operations
                
                Example custom indicator pattern:
                ```python
                def calculate_custom_momentum_score(df, rsi_period=14, vol_period=20):
                    '''Custom momentum indicator combining RSI and volume.'''
                    # RSI component
                    delta = df['close'].diff()
                    gain = delta.where(delta > 0, 0).rolling(rsi_period).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
                    rsi = 100 - (100 / (1 + gain / loss))
                    
                    # Volume component (normalized)
                    vol_sma = df['volume'].rolling(vol_period).mean()
                    vol_score = df['volume'] / vol_sma
                    
                    # Composite score
                    return (rsi / 100) * vol_score  # 0-1 scaled with volume boost
                ```
                
                **BACKTESTING FRAMEWORK:**
                Always include evaluation when creating indicators:
                ```python
                def backtest_signals(df, signal_col, forward_periods=[1, 5, 10]):
                    '''Evaluate signal quality with forward returns.'''
                    results = {}
                    for period in forward_periods:
                        df[f'fwd_ret_{period}'] = df['close'].pct_change(period).shift(-period)
                        
                        # Signal performance
                        buy_signals = df[df[signal_col] == 1]
                        sell_signals = df[df[signal_col] == -1]
                        
                        results[f'{period}_period'] = {
                            'buy_avg_return': buy_signals[f'fwd_ret_{period}'].mean(),
                            'sell_avg_return': sell_signals[f'fwd_ret_{period}'].mean(),
                            'buy_win_rate': (buy_signals[f'fwd_ret_{period}'] > 0).mean(),
                            'signal_count': len(buy_signals) + len(sell_signals)
                        }
                    return results
                ```
                
                **EVALUATION METRICS TO COMPUTE:**
                - Win rate (% profitable signals)
                - Average return per signal
                - Sharpe ratio of strategy vs buy-and-hold
                - Maximum drawdown
                - Profit factor (gross profits / gross losses)
                - Signal frequency (trades per day/week)
                
                **AVAILABLE MODULES:**
                
                🦎 crypto_tools (CoinGecko-based, use coin IDs like 'bitcoin', 'ethereum'):
                - get_crypto_price(symbol) - Current price and stats
                - get_historical_data(symbol, days) - Historical price data
                - get_market_info(symbol) - Detailed market info
                
                🦎 crypto_charts:
                - create_crypto_chart(symbol, days, indicators) - Generate charts
                
                🔶 exchange_tools (Bitget + multi-exchange, use pairs like 'BTCUSDT'):
                - get_realtime_price(symbol, provider) - Real-time price from Bitget or CoinGecko
                - get_price_comparison(symbol) - Compare prices across exchanges
                - get_orderbook_depth(symbol, levels) - Order book depth
                - get_ohlcv_data(symbol, interval, limit) - Candlestick data
                - get_recent_market_trades(symbol, limit) - Recent trades
                - get_futures_data(symbol) - Futures info (funding rate, open interest)
                - get_futures_candles(symbol, interval, limit) - Futures OHLCV
                - get_account_balance(account_type) - Account balances ('spot' or 'futures')
                - check_exchange_status() - Check connected exchanges
                
                Standard libraries: requests, json, pandas, numpy, datetime, pathlib, scipy.stats
                
                **SYMBOL FORMATS:**
                - CoinGecko (crypto_tools): lowercase IDs → 'bitcoin', 'ethereum', 'sui'
                - Bitget (exchange_tools): trading pairs → 'BTCUSDT', 'ETHUSDT', 'SUIUSDT'
                
                Example import patterns:
                ```python
                # For CoinGecko data
                from crypto_tools import get_crypto_price, get_historical_data
                
                # For Bitget/exchange data
                from exchange_tools import get_realtime_price, get_ohlcv_data, get_futures_data
                
                import json
                import pandas as pd
                import numpy as np
                ```
                
                - Save outputs to the 'outputs' directory
                - Include error handling with try/except blocks
                - Make code clear and well-commented
                - **Always evaluate custom indicators before recommending them**
                
                Focus on creating actionable, data-validated insights.""",
                description="Python developer for crypto analysis, custom indicators, and backtesting",
            )
            
            # Report Writer - creates professional Markdown reports
            report_writer = AssistantAgent(
                "ReportWriter",
                model_client=self.model_client,
                tools=report_tools,
                system_message="""You are a professional cryptocurrency report writer specializing in:
                - Creating comprehensive Markdown analysis reports
                - Synthesizing technical and market analysis into readable documents
                - Formatting data, charts, and findings professionally
                - Producing executive summaries and actionable recommendations
                
                Your role is to:
                1. Compile analysis findings from other agents into cohesive reports
                2. Create structured Markdown documents with proper formatting
                3. Summarize complex technical analysis for readability
                4. Generate comparison reports for multiple cryptocurrencies
                5. Document custom indicators with usage instructions
                6. Save all reports to the outputs directory
                
                **REPORT TYPES YOU CAN CREATE:**
                
                📊 **Analysis Reports** (create_analysis_report):
                - Full analysis of a single cryptocurrency
                - Includes price, technical analysis, signals, outlook
                - Use for comprehensive coin reviews
                
                📈 **Comparison Reports** (create_comparison_report):
                - Side-by-side comparison of multiple coins
                - Includes metrics table and recommendations
                - Use for portfolio decisions
                
                🔧 **Custom Indicator Reports** (create_custom_indicator_report):
                - Document new indicator designs
                - Include formula, backtest results, usage guide
                - Use for strategy documentation
                
                📝 **Custom Reports** (save_markdown_report):
                - Flexible format for any analysis
                - Full control over content structure
                - Use for specialized reports
                
                **MARKDOWN FORMATTING GUIDELINES:**
                - Use headers (##) to organize sections
                - Use **bold** for key findings and numbers
                - Use tables for comparing metrics
                - Use bullet points for recommendations
                - Include clear actionable takeaways
                - Add appropriate emojis for visual appeal (📈 📉 🎯 ⚠️)
                
                **REPORT STRUCTURE:**
                1. Executive Summary (2-3 key points)
                2. Data & Analysis (detailed findings)
                3. Signals & Recommendations
                4. Risk Factors & Considerations
                5. Conclusion with actionable steps
                
                Always save reports using the provided tools. Reports are saved to the outputs/ directory.
                Make reports professional, data-driven, and actionable.""",
                description="Professional report writer for Markdown analysis documents",
            )
            
            # Charting Agent - creates professional TradingView-style charts
            charting_agent = AssistantAgent(
                "ChartingAgent",
                model_client=self.model_client,
                tools=tradingview_tools + exchange_tools,
                system_message="""You are a professional charting specialist using TradingView-style visualization.
                
                Your expertise includes:
                - Creating interactive candlestick charts with Lightweight Charts (TradingView's library)
                - Multi-timeframe analysis dashboards
                - AI-annotated charts with buy/sell signals
                - Strategy backtest visualizations
                - Live data chart generation with UDF server
                - **AI Smart Alerts Dashboard** - The ULTIMATE trading tool!
                
                **YOUR CHARTING TOOLS:**
                
                📊 **generate_tradingview_chart(symbol, interval, indicators, theme, title, annotations)**
                Creates a professional TradingView-style interactive chart.
                - symbol: Trading pair like 'BTCUSDT', 'ETHUSDT'
                - interval: '1m', '5m', '15m', '1H', '4H', '1D', '1W'
                - indicators: 'rsi', 'macd', 'bollinger', 'sma', 'ema', 'volume' (comma-separated)
                - theme: 'dark' or 'light'
                - annotations: JSON array of markers [{time, text, position, color}]
                
                📈 **generate_multi_timeframe_dashboard(symbol, timeframes)**
                Creates a dashboard showing the same symbol across multiple timeframes.
                - timeframes: '15m,1H,4H,1D' (comma-separated)
                Perfect for trend alignment analysis!
                
                🎯 **create_ai_annotated_chart(symbol, analysis_signals, support_resistance, trend_lines)**
                Creates charts with AI-powered annotations.
                - analysis_signals: JSON array of signals [{time, type: 'buy'/'sell', description}]
                - support_resistance: Optional S/R levels
                Best for communicating trading ideas!
                
                📉 **generate_strategy_backtest_chart(symbol, strategy_name, trades, equity_curve, metrics)**
                Creates comprehensive backtest visualizations.
                - trades: JSON array [{entry_time, exit_time, entry_price, exit_price, type, profit}]
                - equity_curve: Optional [{time, value}]
                - metrics: {win_rate, profit_factor, max_drawdown}
                Essential for validating strategies!
                
                🔴 **UDF Server Controls (for live data):**
                - start_udf_server(port) - Start live data server
                - stop_udf_server() - Stop the server
                - get_udf_server_status() - Check if server is running
                - generate_live_chart_with_data(symbol, interval) - Chart connected to live server
                
                🚨 **SMART ALERTS - THE ULTIMATE TRADING TOOL:**
                
                **generate_smart_alerts_dashboard(symbols, alert_types, timeframes, min_score)**
                Creates an AI-powered alerts dashboard that:
                - Scans multiple symbols for high-probability setups
                - Calculates confluence scores from multiple indicators
                - Generates mini-charts for each alert
                - Provides specific entry/stop/target levels
                - alert_types: 'divergence,breakout,confluence,reversal'
                
                **create_trade_idea_alert(symbol, direction, entry_price, stop_loss, take_profit, signals)**
                Creates a focused single-trade idea with:
                - Full-size annotated chart
                - Entry, stop, target with R:R ratio
                - Supporting signals list
                - Confidence rating
                
                **WORKFLOW FOR BEST RESULTS:**
                
                1. **Simple Analysis Chart:**
                   Use generate_tradingview_chart with indicators you need
                   
                2. **Trend Analysis:**
                   Use generate_multi_timeframe_dashboard to see trend alignment
                   
                3. **Signal Visualization:**
                   Get signals from TechnicalAnalyst, then use create_ai_annotated_chart
                   
                4. **Strategy Validation:**
                   After CryptoAnalysisCoder backtests, use generate_strategy_backtest_chart
                   
                5. **Live Monitoring:**
                   Start UDF server, then generate_live_chart_with_data for real-time updates
                   
                6. **Trading Alerts:**
                   Use generate_smart_alerts_dashboard for multi-symbol scanning
                   Use create_trade_idea_alert for specific high-conviction setups
                
                **CHARTING BEST PRACTICES:**
                - Always use dark theme for professional look
                - Include volume in most charts
                - For trend analysis, show 4H + 1D timeframes at minimum
                - Annotate key levels (support/resistance)
                - Save charts to outputs/charts/ directory
                - Provide the open_command to let users view charts easily
                
                **COLLABORATION WITH OTHER AGENTS:**
                - TechnicalAnalyst: Provides signals and levels to visualize
                - CryptoAnalysisCoder: Provides backtest trades to chart
                - ReportWriter: Can embed chart links in reports
                - CryptoMarketAnalyst: Provides market context for alerts
                
                After generating a chart, always tell the user how to open it!
                Example: "Open the chart with: open /path/to/chart.html" """,
                description="TradingView charting specialist for interactive visualizations, dashboards, and smart alerts",
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
                participants=[market_analyst, technical_analyst, charting_agent, coder, report_writer, executor],
                model_client=self.model_client,
                max_turns=self.config.max_turns,
                max_stalls=self.config.max_stalls,
            )
            
        self.console.print("✅ [green]Crypto analysis team initialized successfully![/green]\n")
        return team
    
    async def run_task(self, task: str, save_output: bool = True, conversation_mode: bool = False) -> str:
        """
        Execute a task using the MagenticOne team.
        
        Args:
            task: The task description
            save_output: Whether to save the output to a file
            conversation_mode: If True, maintains context between tasks
            
        Returns:
            The task result
        """
        self.console.print(Panel(
            f"[bold cyan]Task:[/bold cyan]\n{task}",
            border_style="cyan"
        ))
        
        # In conversation mode, build context from history
        if conversation_mode and self.conversation_history:
            # Build context summary from previous turns
            context_parts = ["[CONVERSATION CONTEXT - Previous interactions in this session:]"]
            for i, turn in enumerate(self.conversation_history[-5:], 1):  # Last 5 turns
                context_parts.append(f"\n--- Turn {i} ---")
                context_parts.append(f"User: {turn['task']}")
                # Truncate long answers to keep context manageable
                answer = turn['answer']
                if len(answer) > 500:
                    answer = answer[:500] + "... [truncated]"
                context_parts.append(f"Result: {answer}")
            context_parts.append("\n[END CONTEXT]\n")
            context_parts.append(f"Current request: {task}")
            
            augmented_task = "\n".join(context_parts)
        else:
            augmented_task = task
        
        # Initialize team (fresh for each task to avoid state issues)
        team = await self.initialize_team()
        
        # Execute task with minimal console output (task, steps, answer only)
        self.console.print("\n[yellow]🚀 Starting task execution...[/yellow]\n")
        
        try:
            result = await self._process_stream_minimal(team.run_stream(task=augmented_task))
            
            # Extract the answer for conversation history
            answer_text = ""
            if result and result.messages:
                for msg in reversed(result.messages):
                    if isinstance(msg, (TextMessage, StopMessage)):
                        content = getattr(msg, 'content', str(msg))
                        if content and not content.startswith("TERMINATE"):
                            answer_text = content
                            break
            
            # Store in conversation history
            if conversation_mode:
                self.conversation_history.append({
                    "task": task,
                    "answer": answer_text,
                    "timestamp": datetime.now().isoformat(),
                })
            
            # Save output if requested
            if save_output:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = self.output_dir / f"task_output_{timestamp}.txt"
                
                with open(output_file, "w") as f:
                    f.write(f"Task: {task}\n\n")
                    f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
                    f.write("="*80 + "\n\n")
                    if result:
                        # Write all messages for full log
                        for msg in result.messages:
                            f.write(f"\n--- {getattr(msg, 'source', 'System')} ---\n")
                            f.write(str(getattr(msg, 'content', msg)) + "\n")
                
                self.console.print(f"\n✅ [green]Full output saved to:[/green] {output_file}")
            
            return str(result) if result else ""
            
        except asyncio.CancelledError:
            self.console.print("\n\n⚠️ [yellow]Task cancelled by user.[/yellow]")
            raise
        except Exception as e:
            self.console.print(f"\n❌ [red]Error during task execution:[/red] {str(e)}")
            raise
    
    def clear_conversation(self):
        """Clear conversation history to start fresh."""
        self.conversation_history = []
        self.console.print("🗑️  [yellow]Conversation history cleared.[/yellow]")
    
    def show_conversation_history(self):
        """Display the conversation history."""
        if not self.conversation_history:
            self.console.print("[dim]No conversation history yet.[/dim]")
            return
        
        self.console.print("\n[bold cyan]📜 Conversation History:[/bold cyan]")
        for i, turn in enumerate(self.conversation_history, 1):
            self.console.print(f"\n[bold]Turn {i}[/bold] ({turn['timestamp'][:19]})")
            self.console.print(f"  [green]You:[/green] {turn['task'][:100]}{'...' if len(turn['task']) > 100 else ''}")
            answer_preview = turn['answer'][:150] if turn['answer'] else "(no answer)"
            self.console.print(f"  [blue]AI:[/blue] {answer_preview}{'...' if len(turn['answer']) > 150 else ''}")
    
    async def run_interactive_mode(self):
        """Run the crypto analysis platform in interactive mode with conversation support."""
        self.display_banner()
        
        self.console.print("\n[cyan]Welcome to Crypto Analysis Interactive Mode![/cyan]")
        self.console.print("Analyze any cryptocurrency with technical indicators and charts.")
        self.console.print("\n[yellow]Popular coins:[/yellow] bitcoin, ethereum, solana, cardano, polkadot, avalanche-2")
        self.console.print("[yellow]Commands:[/yellow] 'Analyze [coin]', 'Compare [coin1] vs [coin2]', 'Chart [coin] [days]'")
        self.console.print("\n[bold magenta]💬 CONVERSATION MODE IS ON[/bold magenta] - Follow-up questions remember previous context!")
        self.console.print("[dim]Special commands: /clear (reset context), /history (show turns), /single (one-shot mode)[/dim]")
        self.console.print("Type 'exit' or 'quit' to stop. Press Ctrl+C to cancel a running task.\n")
        
        conversation_mode = True  # Default to conversation mode
        
        while True:
            try:
                # Show conversation indicator
                if conversation_mode and self.conversation_history:
                    turn_count = len(self.conversation_history)
                    prompt = f"\n[bold green]Crypto Analysis ({turn_count} turns) >[/bold green] "
                else:
                    prompt = "\n[bold green]Crypto Analysis >[/bold green] "
                
                task = self.console.input(prompt)
                
                # Handle special commands
                if task.lower() in ['exit', 'quit', 'q']:
                    self.console.print("\n👋 [yellow]Goodbye![/yellow]")
                    break
                
                if task.lower() == '/clear':
                    self.clear_conversation()
                    continue
                
                if task.lower() == '/history':
                    self.show_conversation_history()
                    continue
                
                if task.lower() == '/single':
                    conversation_mode = not conversation_mode
                    mode_str = "ON 💬" if conversation_mode else "OFF 🔇"
                    self.console.print(f"[magenta]Conversation mode: {mode_str}[/magenta]")
                    if not conversation_mode:
                        self.clear_conversation()
                    continue
                
                if task.lower() == '/help':
                    self.console.print("""
[bold cyan]Available Commands:[/bold cyan]
  /clear   - Clear conversation history and start fresh
  /history - Show previous turns in this conversation
  /single  - Toggle between conversation mode and one-shot mode
  /help    - Show this help message
  exit     - Exit the application

[bold cyan]Conversation Mode:[/bold cyan]
  When ON, agents remember previous questions and answers.
  Ask follow-up questions like "now do the same for ETH" or "explain that further".
""")
                    continue
                
                if not task.strip():
                    continue
                
                # Execute task with conversation mode
                await self.run_task(task, conversation_mode=conversation_mode)
                
            except KeyboardInterrupt:
                self.console.print("\n\n👋 [yellow]Interrupted by user. Goodbye![/yellow]")
                break
            except asyncio.CancelledError:
                self.console.print("\n\n👋 [yellow]Cancelled. Goodbye![/yellow]")
                break
            except Exception as e:
                self.console.print(f"\n❌ [red]Error:[/red] {str(e)}")
                continue


# Global flag for shutdown
_shutdown_requested = False


def _signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) for graceful shutdown."""
    global _shutdown_requested
    _shutdown_requested = True
    print("\n\n⚠️  Shutdown requested. Stopping gracefully...")
    # Cancel all running tasks in the current event loop
    try:
        loop = asyncio.get_running_loop()
        for task in asyncio.all_tasks(loop):
            if not task.done():
                task.cancel()
    except RuntimeError:
        # No running loop
        pass


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
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except asyncio.CancelledError:
        print("\n\n👋 Task cancelled. Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
