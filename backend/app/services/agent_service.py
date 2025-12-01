"""
Agent Service - Wraps MagenticOne for API use.

This is the critical adapter that converts the console-based
CryptoAnalysisPlatform into a streaming API service.
"""
import asyncio
import sys
from datetime import datetime
from typing import AsyncIterator, Optional, List, Dict, Any
from pathlib import Path
import logging

# Add src to path for existing modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import (
    TextMessage,
    ThoughtEvent,
    ToolCallRequestEvent,
    ToolCallExecutionEvent,
    StopMessage,
    ToolCallSummaryMessage,
)
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor

from app.core.config import get_settings
from app.models.events import (
    AgentStepEvent,
    ToolCallEvent,
    ToolResultEvent,
    FinalResultEvent,
    ErrorEvent,
    ProgressEvent,
    ChartGeneratedEvent,
    StatusEvent,
)

logger = logging.getLogger(__name__)

# Agent emojis for UI display
AGENT_EMOJIS = {
    'CryptoMarketAnalyst': '📊',
    'TechnicalAnalyst': '📈',
    'CryptoAnalysisCoder': '👨‍💻',
    'ReportWriter': '📝',
    'ChartingAgent': '📉',
    'Executor': '🖥️',
}


class AgentService:
    """
    Service for running MagenticOne agents with streaming output.
    
    Converts the Rich console output pattern used in src/main.py
    to WebSocket-friendly events for real-time frontend updates.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._model_client = None  # Lazy initialization
        self.conversation_history: List[Dict[str, str]] = []
        self._cancelled = False
    
    @property
    def model_client(self):
        """Lazy initialization of model client."""
        if self._model_client is None:
            self._model_client = self._create_model_client()
        return self._model_client
    
    def _create_model_client(self):
        """Create the appropriate LLM client based on configuration."""
        if self.settings.llm_provider == "azure":
            from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
            
            model_info = {
                "vision": True,
                "function_calling": True,
                "json_output": True,
                "structured_output": True,
                "family": "gpt-4",
            }
            
            return AzureOpenAIChatCompletionClient(
                azure_deployment=self.settings.azure_openai_deployment,
                api_version=self.settings.azure_openai_api_version,
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                model=self.settings.azure_openai_deployment,
                model_info=model_info,
            )
        else:
            # Ollama fallback - for now, log a warning and use Azure if available
            logger.warning(
                "Ollama provider requested but not implemented. "
                "Please set LLM_PROVIDER=azure and configure Azure OpenAI credentials."
            )
            # Raise error to prevent silent failures
            raise NotImplementedError(
                "Ollama provider not yet implemented. "
                "Please set LLM_PROVIDER=azure in your environment."
            )
    
    async def _create_team(self) -> MagenticOneGroupChat:
        """
        Create the MagenticOne team with all specialized crypto agents.
        
        This mirrors the team setup in src/main.py but configured for API use.
        """
        # Import crypto tools
        from crypto_tools import get_crypto_price, get_historical_data, get_market_info
        from crypto_charts import create_crypto_chart
        from exchange_tools import (
            get_realtime_price, get_price_comparison, get_orderbook_depth,
            get_ohlcv_data, get_recent_market_trades, get_futures_data,
            get_futures_candles, get_account_balance, check_exchange_status,
        )
        from report_tools import (
            save_markdown_report, create_analysis_report,
            create_comparison_report, create_custom_indicator_report,
        )
        from indicator_registry import (
            save_custom_indicator, list_custom_indicators,
            get_custom_indicator, delete_custom_indicator,
            get_indicator_code_for_execution,
        )
        from tradingview_tools import (
            generate_tradingview_chart, create_ai_annotated_chart,
            generate_multi_timeframe_dashboard, generate_strategy_backtest_chart,
        )
        from smart_alerts import (
            generate_smart_alerts_dashboard, create_trade_idea_alert,
        )
        
        # Define tool sets
        coingecko_tools = [get_crypto_price, get_historical_data, get_market_info, create_crypto_chart]
        exchange_tools_list = [
            get_realtime_price, get_price_comparison, get_orderbook_depth,
            get_ohlcv_data, get_recent_market_trades, get_futures_data,
            get_futures_candles, get_account_balance, check_exchange_status,
        ]
        report_tools_list = [
            save_markdown_report, create_analysis_report,
            create_comparison_report, create_custom_indicator_report,
        ]
        indicator_tools_list = [
            save_custom_indicator, list_custom_indicators,
            get_custom_indicator, delete_custom_indicator,
            get_indicator_code_for_execution,
        ]
        tradingview_tools_list = [
            generate_tradingview_chart, create_ai_annotated_chart,
            generate_multi_timeframe_dashboard, generate_strategy_backtest_chart,
            generate_smart_alerts_dashboard, create_trade_idea_alert,
        ]
        
        all_crypto_tools = coingecko_tools + exchange_tools_list
        
        # Create agents with system messages (abbreviated for clarity)
        market_analyst = AssistantAgent(
            "CryptoMarketAnalyst",
            model_client=self.model_client,
            tools=all_crypto_tools,
            system_message="""You are a cryptocurrency market analyst with deep expertise in:
- Crypto market dynamics and trends
- Market cap analysis and ranking
- Volume analysis and liquidity assessment
- Real-time exchange data analysis

Your role is to fetch and analyze crypto prices, track changes, analyze market cap and volume,
identify trends, and compare prices across exchanges.

DATA SOURCES:
- CoinGecko: Use coin IDs like 'bitcoin', 'ethereum', 'solana'
- Bitget: Use trading pairs like 'BTCUSDT', 'ETHUSDT'

Always provide clear, data-driven insights with specific numbers.""",
            description="Expert in crypto markets, trends, and fundamental analysis",
        )
        
        technical_analyst = AssistantAgent(
            "TechnicalAnalyst",
            model_client=self.model_client,
            tools=all_crypto_tools + indicator_tools_list,
            system_message="""You are a cryptocurrency technical analyst specializing in:
- Chart pattern recognition
- Technical indicators (RSI, MACD, Bollinger Bands, Moving Averages)
- Support/resistance levels
- Trading signals and entry/exit points
- Futures market analysis

Guidelines:
- RSI < 30 = Oversold (potential buy)
- RSI > 70 = Overbought (potential sell)
- MACD crossover = Trend change signal

Always explain your technical findings in clear terms.""",
            description="Expert in technical analysis, charts, and indicators",
        )
        
        charting_agent = AssistantAgent(
            "ChartingAgent",
            model_client=self.model_client,
            tools=tradingview_tools_list + exchange_tools_list,
            system_message="""You are a professional charting specialist using TradingView-style visualization.

Your tools:
- generate_tradingview_chart: Create interactive candlestick charts
- generate_multi_timeframe_dashboard: Multi-TF analysis
- create_ai_annotated_chart: Charts with AI signals
- generate_strategy_backtest_chart: Backtest visualizations
- generate_smart_alerts_dashboard: AI trading alerts

Symbol format: 'BTCUSDT', 'ETHUSDT' (trading pairs)
Intervals: '1m', '5m', '15m', '1H', '4H', '1D', '1W'""",
            description="TradingView charting specialist",
        )
        
        coder = AssistantAgent(
            "CryptoAnalysisCoder",
            model_client=self.model_client,
            tools=indicator_tools_list,
            system_message="""You are a Python developer for crypto analysis and custom indicators.

Your role:
1. Write Python scripts for advanced analysis
2. Implement custom indicators designed by TechnicalAnalyst
3. Backtest and evaluate indicator performance
4. Save indicators to the registry for reuse

Always check for existing indicators before creating new ones.
Save working indicators so they can be reused in future sessions.""",
            description="Python developer for analysis and custom indicators",
        )
        
        report_writer = AssistantAgent(
            "ReportWriter",
            model_client=self.model_client,
            tools=report_tools_list,
            system_message="""You are a professional cryptocurrency report writer.

Report types:
- Analysis Reports: Full analysis of a single cryptocurrency
- Comparison Reports: Side-by-side comparison of multiple coins
- Custom Indicator Reports: Document new indicator designs

Use proper Markdown formatting with headers, bold text, tables, and bullet points.
Include executive summary, analysis, recommendations, and risk factors.""",
            description="Report writer for analysis documents",
        )
        
        # Create code executor for running analysis scripts
        output_dir = Path(self.settings.output_dir) / "code_execution"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        code_executor = LocalCommandLineCodeExecutor(work_dir=str(output_dir))
        executor = CodeExecutorAgent("Executor", code_executor=code_executor)
        
        # Create the team
        return MagenticOneGroupChat(
            participants=[
                market_analyst,
                technical_analyst,
                charting_agent,
                coder,
                report_writer,
                executor,
            ],
            model_client=self.model_client,
            max_turns=self.settings.max_turns,
            max_stalls=self.settings.max_stalls,
        )
    
    async def run_streaming(self, message: str) -> AsyncIterator:
        """
        Run an agent task with streaming events.
        
        This is the key method that converts console output patterns
        to WebSocket events for real-time frontend updates.
        
        Args:
            message: The user's query/task
            
        Yields:
            Pydantic event models (AgentStepEvent, ToolCallEvent, etc.)
        """
        self._cancelled = False
        
        # Send initial status
        yield StatusEvent(
            status="initializing",
            message="Initializing agent team...",
            timestamp=datetime.now(),
        )
        
        try:
            team = await self._create_team()
        except Exception as e:
            logger.exception("Failed to create agent team")
            yield ErrorEvent(
                message="Failed to initialize agents",
                details=str(e),
                recoverable=False,
                timestamp=datetime.now(),
            )
            return
        
        # Send ready status
        yield StatusEvent(
            status="processing",
            message="Agent team ready, processing query...",
            timestamp=datetime.now(),
        )
        
        last_agent = None
        turn_count = 0
        agents_used = []
        
        try:
            async for msg in team.run_stream(task=message):
                if self._cancelled:
                    yield StatusEvent(
                        status="cancelled",
                        message="Task cancelled by user",
                        timestamp=datetime.now(),
                    )
                    break
                
                # Handle TaskResult (final result)
                if isinstance(msg, TaskResult):
                    # Extract final answer from messages
                    final_content = None
                    for m in reversed(msg.messages):
                        if isinstance(m, (TextMessage, StopMessage)):
                            content = getattr(m, 'content', str(m))
                            if content and not content.startswith("TERMINATE"):
                                final_content = content
                                break
                    
                    if final_content:
                        yield FinalResultEvent(
                            content=final_content,
                            format="markdown",
                            agents_used=agents_used,
                            timestamp=datetime.now(),
                        )
                    else:
                        # No valid final result found
                        yield StatusEvent(
                            status="completed",
                            message="Analysis completed",
                            timestamp=datetime.now(),
                        )
                    continue
                
                # Get source/agent name
                source = getattr(msg, 'source', None)
                
                # Emit agent step event when agent changes
                if source and source != last_agent:
                    turn_count += 1
                    if source not in agents_used:
                        agents_used.append(source)
                    
                    yield AgentStepEvent(
                        agent=source,
                        emoji=AGENT_EMOJIS.get(source, '🤖'),
                        status="working",
                        message=f"{source} is analyzing...",
                        timestamp=datetime.now(),
                    )
                    
                    yield ProgressEvent(
                        current_turn=turn_count,
                        max_turns=self.settings.max_turns,
                        percentage=min((turn_count / self.settings.max_turns) * 100, 100),
                        timestamp=datetime.now(),
                    )
                    
                    last_agent = source
                
                # Emit tool call events
                if isinstance(msg, ToolCallRequestEvent):
                    for call in msg.content:
                        tool_name = getattr(call, 'name', str(call))
                        arguments = getattr(call, 'arguments', None)
                        
                        yield ToolCallEvent(
                            agent=source or "unknown",
                            tool_name=tool_name,
                            arguments=arguments if isinstance(arguments, dict) else None,
                            timestamp=datetime.now(),
                        )
                        
                        # Send progress update for chart generation
                        if 'chart' in tool_name.lower() or 'dashboard' in tool_name.lower():
                            yield StatusEvent(
                                status="processing",
                                message=f"Generating {tool_name}...",
                                timestamp=datetime.now(),
                            )
                
                # Emit tool result events
                if isinstance(msg, ToolCallExecutionEvent):
                    for result in msg.content:
                        call_id = getattr(result, 'call_id', 'unknown')
                        content = getattr(result, 'content', '')
                        
                        # Check if this is a chart result
                        if isinstance(content, str) and ('chart' in content.lower() or '.html' in content):
                            # Try to extract chart info from result
                            try:
                                import json
                                if content.startswith('{'):
                                    chart_data = json.loads(content)
                                    # Check for various chart file keys
                                    chart_path = chart_data.get('chart_file') or chart_data.get('file') or chart_data.get('path', '')
                                    if chart_path and chart_data.get('status') == 'success':
                                        # Extract filename from path
                                        filename = Path(chart_path).name
                                        yield ChartGeneratedEvent(
                                            chart_id=call_id,
                                            url=f"/charts/{filename}",
                                            symbol=chart_data.get('symbol', 'unknown'),
                                            interval=chart_data.get('interval', ''),
                                            timestamp=datetime.now(),
                                        )
                                        logger.info(f"Chart generated: {filename} for {chart_data.get('symbol')}")
                            except (json.JSONDecodeError, Exception) as e:
                                logger.debug(f"Not a JSON chart result: {e}")
                        
                        yield ToolResultEvent(
                            tool_name=call_id,
                            success=True,
                            result_preview=str(content)[:200] if content else None,
                            timestamp=datetime.now(),
                        )
        
        except asyncio.CancelledError:
            logger.info("Agent task cancelled")
            yield ErrorEvent(
                message="Task cancelled",
                details="The analysis was cancelled by the user",
                recoverable=True,
                timestamp=datetime.now(),
            )
        except Exception as e:
            logger.exception("Error during agent execution")
            yield ErrorEvent(
                message="Agent execution failed",
                details=str(e),
                recoverable=True,
                timestamp=datetime.now(),
            )
    
    async def cancel(self):
        """Cancel the current running task."""
        self._cancelled = True
        logger.info("Agent task cancellation requested")
    
    def add_to_history(self, role: str, content: str):
        """Add a message to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
