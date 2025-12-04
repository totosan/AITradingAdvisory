"""
Agent Service - Wraps MagenticOne for API use.

This is the critical adapter that converts the console-based
CryptoAnalysisPlatform into a streaming API service.

Includes intent detection to route simple queries (like price lookups)
directly to tools without orchestrating the full multi-agent team.
"""
import asyncio
import sys
import json
import re
from datetime import datetime
from typing import AsyncIterator, Optional, List, Dict, Any, Union
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
    QuickResultEvent,
    ErrorEvent,
    ProgressEvent,
    ChartGeneratedEvent,
    StatusEvent,
)

# Import intent router
from intent_router import IntentRouter, IntentType, Intent, format_simple_result

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


ChartContent = Union[str, Dict[str, Any], List[Any]]


def _extract_chart_data(content: ChartContent) -> Optional[Dict[str, Any]]:
    """Extract structured chart info from various Autogen result shapes."""
    if content is None:
        return None

    # Direct dict payload already structured
    if isinstance(content, dict):
        # Autogen can wrap text payloads in {"type": "output_text", "text": "..."}
        text_field = content.get("text")
        if isinstance(text_field, str):
            return _extract_chart_data(text_field)
        return content

    # Lists typically wrap multiple parts, take the first chart-like entry
    if isinstance(content, list):
        for item in content:
            chart_data = _extract_chart_data(item)
            if chart_data:
                return chart_data
        return None

    # Strings may be JSON or plain text with a chart path reference
    if isinstance(content, str):
        text = content.strip()
        if not text:
            return None

        lowered = text.lower()
        if "chart" not in lowered and ".html" not in lowered:
            return None

        if text.startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        match = re.search(r"(?:/app)?/outputs/charts/([\w\-]+\.html)", text)
        if match:
            filename = match.group(1)
            return {
                "chart_file": f"/outputs/charts/{filename}",
                "filename": filename,
                "status": "success",
            }

    return None


class AgentService:
    """
    Service for running MagenticOne agents with streaming output.
    
    Converts the Rich console output pattern used in src/main.py
    to WebSocket-friendly events for real-time frontend updates.
    
    Includes intent routing to optimize simple queries by executing
    them directly without the full multi-agent orchestration.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._model_client = None  # Lazy initialization
        self.conversation_history: List[Dict[str, str]] = []
        self._cancelled = False
        self._cancel_event = asyncio.Event()
        
        # Initialize intent router with tools
        self._intent_router = IntentRouter()
        self._tools: Dict[str, Any] = {}  # Lazy initialization
        self._tools_initialized = False
    
    @property
    def is_cancelled(self) -> bool:
        """Check if the current task has been cancelled."""
        return self._cancelled
    
    def _initialize_tools(self) -> None:
        """Initialize tools for simple intent execution."""
        if self._tools_initialized:
            return
            
        from exchange_tools import get_realtime_price, get_price_comparison
        from crypto_tools import get_crypto_price, get_market_info
        
        self._tools = {
            "get_realtime_price": get_realtime_price,
            "get_price_comparison": get_price_comparison,
            "get_crypto_price": get_crypto_price,
            "get_market_info": get_market_info,
        }
        
        # Register tools with the router
        for name, func in self._tools.items():
            self._intent_router.register_tool(name, func)
        
        self._tools_initialized = True
        logger.info("Intent router tools initialized")
    
    async def classify_intent(self, message: str) -> Intent:
        """
        Classify the intent of a user message using LLM (with pattern fallback).
        
        Args:
            message: The user's message
            
        Returns:
            Intent object with classification
        """
        # Try LLM-based classification first (smarter)
        try:
            return await self._intent_router.classify_async(message)
        except Exception as e:
            logger.warning(f"LLM classification failed, using pattern fallback: {e}")
            return self._intent_router.classify(message)
    
    async def _execute_simple_intent(self, message: str, intent: Intent) -> Optional[Dict[str, Any]]:
        """
        Execute a simple intent directly without multi-agent orchestration.
        
        Args:
            message: The user's message
            intent: The classified intent
            
        Returns:
            Result dict if successful, None if should fallback to agents
        """
        self._initialize_tools()
        
        result = await self._intent_router.execute_simple(message, intent, self._tools)
        
        if result.get("success"):
            return result
        
        if result.get("fallback_to_agents"):
            logger.info(f"Falling back to agents: {result.get('error')}")
            return None
        
        return result
    
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
            generate_entry_analysis_chart,  # NEW: Entry points visualization
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
            generate_entry_analysis_chart,  # Entry points with SL/TP visualization
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

Always provide clear, data-driven insights with specific numbers.

**MANDATORY CHARTING - ALWAYS REQUEST A CHART!**
After completing your market analysis, you MUST request ChartingAgent to generate a chart.
Every analysis should include a visual chart with indicators and key levels.
Pass support/resistance levels, trends, and analysis insights to ChartingAgent.""",
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

When analyzing for entry points, provide structured data for ChartingAgent:
- Entry prices at key levels
- Stop loss below support (long) or above resistance (short)
- Take profit targets with minimum 2:1 R:R
- Confidence level (high/medium/low) based on confluences

Always explain your technical findings in clear terms.

**MANDATORY CHARTING - ALWAYS REQUEST A CHART!**
After completing technical analysis, you MUST request ChartingAgent to generate a chart.
Provide ChartingAgent with:
- indicators: 'rsi,macd,sma,ema,bollinger' (all you analyzed)
- support_levels: [prices]
- resistance_levels: [prices]  
- entry_points: [{type, price, stop_loss, take_profit, reason, confidence}]

**NEVER complete analysis without requesting a chart from ChartingAgent!**""",
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
- **generate_entry_analysis_chart**: THE KEY TOOL for entry point visualization with SL/TP!

**USE generate_entry_analysis_chart when:**
- User asks for entry points or trade setups
- User wants to see where to buy/sell with stop loss and take profit
- Creating actionable trading visualizations
- ANY analysis request - always include a chart!

**IMPORTANT: Include indicators parameter to show which indicators were used!**
Example: indicators="sma,ema,bollinger,rsi,macd,volume" displays these on the chart
Available indicators: 'sma', 'ema', 'bollinger', 'rsi', 'macd', 'volume'

Entry point format:
[{"type": "long", "price": 98500, "stop_loss": 97000, "take_profit": [100000, 102000], "reason": "Breakout", "confidence": "high"}]

Symbol format: 'BTCUSDT', 'ETHUSDT' (trading pairs)
Intervals: '1m', '5m', '15m', '1H', '4H', '1D', '1W'

**CRITICAL: YOU MUST ALWAYS GENERATE A CHART!**
Whenever you are asked to participate in analysis, you MUST call one of your charting tools.
Do NOT just describe a chart - actually call generate_tradingview_chart or generate_entry_analysis_chart!
Every conversation MUST end with an actual chart file being generated.

Default chart settings:
- theme: 'dark'
- indicators: 'sma,ema,volume,rsi,macd'
- Include all support/resistance levels from analysis
- Add entry points with SL/TP when trading setups exist""",
            description="TradingView charting specialist with entry point visualization",
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

    def _build_prompt_with_history(self, message: str) -> str:
        """Combine prior conversation history with the new user query."""
        if not self.conversation_history:
            return message
        # Use the most recent 8 exchanges for context
        history_slice = self.conversation_history[-8:]
        history_lines = []
        for entry in history_slice:
            role = entry.get("role", "user").capitalize()
            content = entry.get("content", "")
            history_lines.append(f"{role}: {content}")
        history_text = "\n".join(history_lines)
        return (
            "You are continuing an ongoing crypto analysis conversation. "
            "Respect the prior context when responding.\n"
            f"Conversation history:\n{history_text}\n\nUser: {message}"
        )
    
    async def run_streaming(self, message: str) -> AsyncIterator:
        """
        Run an agent task with streaming events.
        
        This is the key method that converts console output patterns
        to WebSocket events for real-time frontend updates.
        
        Uses intent detection to route simple queries directly to tools
        without orchestrating the full multi-agent team.
        
        Args:
            message: The user's query/task
            
        Yields:
            Pydantic event models (AgentStepEvent, ToolCallEvent, etc.)
        """
        # Classify intent first (using LLM with pattern fallback)
        intent = await self.classify_intent(message)
        logger.info(f"Intent classified: {intent.type.value} (confidence: {intent.confidence:.2f})")
        
        # Handle simple intents directly
        if intent.is_simple():
            yield StatusEvent(
                status="processing",
                message="Quick lookup...",
                timestamp=datetime.now(),
            )
            
            result = await self._execute_simple_intent(message, intent)
            
            if result and result.get("success"):
                # Format the result nicely
                formatted = format_simple_result(result)
                
                # Add to history
                self.add_to_history("user", message)
                self.add_to_history("assistant", formatted)
                
                yield QuickResultEvent(
                    content=formatted,
                    symbols=result.get("symbols", []),
                    tool_used=result.get("tool_used", ""),
                    intent_type=intent.type.value,
                    confidence=intent.confidence,
                    timestamp=datetime.now(),
                )
                return
            
            # Fallback to full agent processing if simple execution failed
            logger.info("Simple execution failed, falling back to agents")
        
        # Handle compound intents - execute quick component first, then full processing
        if intent.has_quick_component():
            logger.info(f"Compound query detected: {intent.type.value} with sub-intents {[s.value for s in intent.sub_intents]}")
            
            yield StatusEvent(
                status="processing",
                message="Fetching quick data first...",
                timestamp=datetime.now(),
            )
            
            # Execute the quick lookup component
            quick_result = await self._execute_simple_intent(message, intent)
            
            if quick_result and quick_result.get("success"):
                formatted = format_simple_result(quick_result)
                
                # Yield quick result first (progressive feedback)
                yield QuickResultEvent(
                    content=f"📊 **Quick Data:**\n{formatted}\n\n⏳ *Now processing full {intent.type.value}...*",
                    symbols=quick_result.get("symbols", []),
                    tool_used=quick_result.get("tool_used", ""),
                    intent_type="compound_preview",
                    confidence=intent.confidence,
                    timestamp=datetime.now(),
                )
            
            # Continue to full agent processing for the main intent
        
        # Full agent processing for complex intents
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
        prompt = self._build_prompt_with_history(message)
        self.add_to_history("user", message)
        
        try:
            async for msg in team.run_stream(task=prompt):
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
                        self.add_to_history("assistant", final_content)
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
                        logger.debug(f"Tool result content type: {type(content)}, preview: {str(content)[:200]}")
                        chart_data = _extract_chart_data(content)
                        logger.debug(f"Extracted chart_data: {chart_data}")

                        if chart_data:
                            chart_path = None
                            for key in (
                                'chart_file', 'dashboard_file', 'file',
                                'path', 'html_file', 'report_file', 'output_path'
                            ):
                                candidate = chart_data.get(key)
                                if candidate:
                                    chart_path = candidate
                                    break

                            chart_url = chart_data.get('url')
                            normalized_url = None

                            if chart_path and chart_data.get('status') == 'success':
                                filename = Path(chart_path).name
                                normalized_url = chart_url or f"/charts/{filename}"
                            elif chart_url:
                                normalized_url = chart_url

                            # Final fallback when only filename is available
                            if not normalized_url and chart_path:
                                filename = Path(chart_path).name
                                normalized_url = f"/charts/{filename}"

                            if normalized_url:
                                if normalized_url.startswith('/app/outputs/charts/'):
                                    normalized_url = normalized_url.replace('/app', '', 1)
                                if normalized_url.startswith('/outputs/charts/'):
                                    normalized_url = normalized_url.replace('/outputs/charts/', '/charts/', 1)
                                if not normalized_url.startswith('/') and not normalized_url.startswith('http'):
                                    normalized_url = f"/charts/{normalized_url}"

                                logger.info(f"Chart URL normalized: {normalized_url}")

                                timeframes = chart_data.get('timeframes')
                                interval_value = chart_data.get('interval')
                                if not interval_value and isinstance(timeframes, list):
                                    interval_value = ','.join(timeframes)
                                elif not interval_value and isinstance(timeframes, str):
                                    interval_value = timeframes

                                yield ChartGeneratedEvent(
                                    chart_id=call_id,
                                    url=normalized_url,
                                    symbol=chart_data.get('symbol') or chart_data.get('symbols') or 'unknown',
                                    interval=interval_value or '',
                                    timestamp=datetime.now(),
                                )
                                logger.info(
                                    "Chart generated: %s for %s",
                                    normalized_url,
                                    chart_data.get('symbol') or chart_data.get('symbols'),
                                )
                        
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
        self._cancel_event.set()
        logger.info("Agent task cancellation requested")
    
    def reset_cancellation(self):
        """Reset cancellation state for a new request."""
        self._cancelled = False
        self._cancel_event.clear()
        logger.debug("Cancellation state reset")
    
    def add_to_history(self, role: str, content: str):
        """Add a message to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        # Keep only the most recent 20 entries (10 user/assistant exchanges)
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
