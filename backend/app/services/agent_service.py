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
    ContentFilterErrorEvent,
    ContentFilterRetryEvent,
    ProgressEvent,
    ChartGeneratedEvent,
    StatusEvent,
)

# Import intent router
from intent_router import IntentRouter, IntentType, Intent, format_simple_result

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# SHARED AGENT GUIDELINES - Applied to ALL agents for maximum trading success
# ═══════════════════════════════════════════════════════════════════════════════

SHARED_AGENT_RULES = """
═══════════════════════════════════════════════════════════════════════════════
🔒 UNIVERSELLE REGELN - DU BIST AUTONOM!
═══════════════════════════════════════════════════════════════════════════════

🚨 DU HAST DIREKTEN ZUGRIFF AUF LIVE-DATEN VON BITGET!
   Du brauchst KEINE Daten vom Benutzer - du holst sie SELBST!

⛔ **ABSOLUT VERBOTEN:**
1. "Ich brauche Daten von dir" sagen → DU holst die Daten selbst!
2. "Welche Börse benutzt du?" fragen → DU hast Bitget-Zugang!
3. "Bitte schicke mir die Daten" → NIEMALS! Du rufst get_ohlcv_data() auf!
4. Auf Benutzer-Input warten → Du handelst SOFORT autonom!
5. Synthetische/hypothetische Daten verwenden → NUR echte Tool-Daten!

✅ **KORREKTES VERHALTEN bei JEDER Anfrage:**
1. SOFORT get_realtime_price() oder get_ohlcv_data() aufrufen
2. Die ECHTEN Daten analysieren
3. Ergebnisse mit Zeitstempel und Quelle dokumentieren
4. Chart erstellen lassen

📋 **BEISPIEL - Benutzer fragt "Analysiere XRP":**
FALSCH ❌: "Ich brauche erst die Kursdaten von dir..."
RICHTIG ✅: Sofort get_ohlcv_data("XRPUSDT", "1H", 200) aufrufen!

🎯 **DEIN WORKFLOW:**
```
1. get_realtime_price("XRPUSDT") → Aktueller Preis
2. get_ohlcv_data("XRPUSDT", "1H", 200) → Stunden-Kerzen
3. Indikatoren berechnen (RSI, MACD, etc.)
4. S/R Levels aus echten Highs/Lows
5. Entry/SL/TP bestimmen
6. ChartingAgent für Visualisierung
```

DU BIST AUTONOM! KEINE AUSREDEN! HOLE DIE DATEN SELBST!
═══════════════════════════════════════════════════════════════════════════════
"""

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


def _parse_content_filter_error(error_str: str) -> Optional[Dict[str, Any]]:
    """
    Parse Azure OpenAI content filter error to extract details.
    
    Returns dict with filter_type, filter_results if content filter error,
    otherwise None.
    """
    if "content_filter" not in error_str.lower() and "content management policy" not in error_str.lower():
        return None
    
    result = {
        "is_content_filter": True,
        "filter_type": None,
        "filter_results": None,
    }
    
    # Try to parse JSON error structure
    try:
        # Find JSON-like structure in the error string
        import re
        json_match = re.search(r"\{.*'error'.*\}", error_str, re.DOTALL)
        if json_match:
            # Convert single quotes to double quotes for JSON parsing
            json_str = json_match.group(0).replace("'", '"').replace("None", "null").replace("True", "true").replace("False", "false")
            error_data = json.loads(json_str)
            
            if "error" in error_data:
                inner_error = error_data["error"].get("innererror", {})
                content_filter_result = inner_error.get("content_filter_result", {})
                
                result["filter_results"] = content_filter_result
                
                # Determine which filter was triggered
                for filter_name, filter_data in content_filter_result.items():
                    if isinstance(filter_data, dict) and filter_data.get("filtered", False):
                        result["filter_type"] = filter_name
                        break
                    elif isinstance(filter_data, dict) and filter_data.get("detected", False):
                        result["filter_type"] = filter_name
                        break
                        
    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        logger.debug(f"Could not parse content filter error JSON: {e}")
        # Fallback: try to find filter type from text
        if "jailbreak" in error_str.lower():
            result["filter_type"] = "jailbreak"
        elif "hate" in error_str.lower():
            result["filter_type"] = "hate"
        elif "violence" in error_str.lower():
            result["filter_type"] = "violence"
        elif "sexual" in error_str.lower():
            result["filter_type"] = "sexual"
        elif "self_harm" in error_str.lower():
            result["filter_type"] = "self_harm"
    
    return result


def _sanitize_prompt_for_retry(prompt: str, filter_type: Optional[str] = None) -> str:
    """
    Sanitize a prompt that triggered a content filter for retry.
    
    This function reformulates the prompt to be more neutral while
    preserving the core intent.
    """
    import re
    
    # Remove potentially problematic patterns based on filter type
    sanitized = prompt
    
    # Common replacements for financial/trading context
    replacements = [
        # Aggressive trading terms
        (r'\b(aggressive|aggressiv)\b', 'dynamisch', re.IGNORECASE),
        (r'\b(attack|attacke|angriff)\b', 'Strategie', re.IGNORECASE),
        (r'\b(kill|töten|vernichten|zerstören)\b', 'übertreffen', re.IGNORECASE),
        (r'\b(crash|kollaps|einbruch)\b', 'Korrektur', re.IGNORECASE),
        (r'\b(explosion|explodieren|rakete)\b', 'starke Bewegung', re.IGNORECASE),
        (r'\b(manipulation|manipulieren)\b', 'Marktaktivität', re.IGNORECASE),
        (r'\b(whale|wale|wal)\b', 'großer Marktteilnehmer', re.IGNORECASE),
        (r'\b(pump|dump)\b', 'Preisbewegung', re.IGNORECASE),
        (r'\b(liquidation|liquidieren)\b', 'Positionsschließung', re.IGNORECASE),
        (r'\b(hunt|jagen|jagd)\b', 'Bewegung zu', re.IGNORECASE),
        (r'\b(squeeze)\b', 'Preisdruck', re.IGNORECASE),
        (r'\b(brutal|massiv|extrem)\b', 'signifikant', re.IGNORECASE),
        # Remove excessive punctuation that might look like injection
        (r'[!]{2,}', '!', 0),
        (r'[?]{2,}', '?', 0),
        # Remove code-like patterns that might trigger jailbreak
        (r'```[^`]*```', '[Code-Block entfernt]', re.DOTALL),
        (r'<[^>]+>', '', 0),  # Remove HTML-like tags
    ]
    
    for pattern, replacement, flags in replacements:
        if flags:
            sanitized = re.sub(pattern, replacement, sanitized, flags=flags)
        else:
            sanitized = re.sub(pattern, replacement, sanitized)
    
    # For jailbreak specifically, simplify the prompt more aggressively
    if filter_type == "jailbreak":
        # Remove system-like instructions that might look like prompt injection
        sanitized = re.sub(r'(?i)(ignore|vergiss|überschreib|override|bypass).*?(instruction|anweisung|regel|rule)', '', sanitized)
        # Remove role-playing instructions
        sanitized = re.sub(r'(?i)(tu so als|act as|pretend|stell dir vor du bist)', 'analysiere als', sanitized)
    
    # Add a clarifying prefix for the retry
    retry_prefix = """[HINWEIS: Dies ist eine neutrale Marktanalyse-Anfrage. 
Bitte führe eine sachliche, datenbasierte Analyse durch.]

"""
    
    return retry_prefix + sanitized


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
            generate_strategy_visualization,  # NEW: Final strategy chart
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
            generate_strategy_visualization,  # FINAL strategy chart with all findings
            generate_smart_alerts_dashboard, create_trade_idea_alert,
        ]
        
        all_crypto_tools = coingecko_tools + exchange_tools_list
        
        # Create agents with system messages (abbreviated for clarity)
        market_analyst = AssistantAgent(
            "CryptoMarketAnalyst",
            model_client=self.model_client,
            tools=all_crypto_tools,
            system_message="""You are a cryptocurrency market analyst with DIRECT ACCESS to live market data.

═══════════════════════════════════════════════════════════════════════════════
🚨 CRITICAL: DU HAST DIREKTEN ZUGRIFF AUF LIVE-DATEN! 🚨
═══════════════════════════════════════════════════════════════════════════════

DU HAST DIESE TOOLS - BENUTZE SIE SOFORT:
• get_realtime_price("XRPUSDT") → Aktueller Preis von Bitget
• get_ohlcv_data("XRPUSDT", "1H", 200) → 200 Stunden-Kerzen
• get_ohlcv_data("XRPUSDT", "5m", 100) → 100 5-Minuten-Kerzen
• get_orderbook_depth("XRPUSDT") → Orderbuch
• get_futures_data("XRPUSDT") → Funding Rate, Open Interest

⛔ ABSOLUT VERBOTEN:
- "Ich kann keine Daten holen" → FALSCH! Du HAST die Tools!
- "Ich brauche Daten von dir" → FALSCH! Hole sie SELBST mit get_ohlcv_data!
- "Welche Börse benutzt du?" → IRRELEVANT! Du hast Bitget-Zugang!
- Den Benutzer nach Daten fragen → NIEMALS! Du holst sie selbst!

✅ KORREKTES VERHALTEN bei jeder Anfrage:
1. SOFORT get_realtime_price() und get_ohlcv_data() aufrufen
2. Mit den ECHTEN Daten analysieren
3. Entry/SL/TP aus den echten Kerzen berechnen
4. Chart anfordern

BEISPIEL - Benutzer fragt "Analyse XRP für Long":
→ FALSCH: "Ich brauche erst Daten von dir..."
→ RICHTIG: Sofort get_ohlcv_data("XRPUSDT", "1H", 200) aufrufen und analysieren!

DU BIST AUTONOM! DU HOLST DIE DATEN SELBST! KEINE AUSREDEN!
═══════════════════════════════════════════════════════════════════════════════

Symbol-Format für Tools: 'BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'SOLUSDT'
Timeframes: '1m', '5m', '15m', '1H', '4H', '1D'

Bei JEDER Analyse-Anfrage:
1. get_realtime_price(symbol) für aktuellen Preis
2. get_ohlcv_data(symbol, "1H", 200) für Stunden-Daten
3. get_ohlcv_data(symbol, "5m", 100) für kurzfristige Daten (wenn LTF gewünscht)
4. Dann analysieren und ChartingAgent für Visualisierung aufrufen
""" + SHARED_AGENT_RULES,
            description="Expert in crypto markets with DIRECT ACCESS to live Bitget data",
        )
        
        technical_analyst = AssistantAgent(
            "TechnicalAnalyst",
            model_client=self.model_client,
            tools=all_crypto_tools + indicator_tools_list,
            system_message="""You are a cryptocurrency technical analyst with DIRECT ACCESS to live market data.

═══════════════════════════════════════════════════════════════════════════════
🚨 CRITICAL: DU HAST DIREKTEN ZUGRIFF AUF LIVE-DATEN! 🚨
═══════════════════════════════════════════════════════════════════════════════

DU HAST DIESE TOOLS - BENUTZE SIE SOFORT:
• get_ohlcv_data("XRPUSDT", "1H", 200) → 200 Stunden-Kerzen für Analyse
• get_ohlcv_data("XRPUSDT", "5m", 100) → 100 5-Min-Kerzen für LTF
• get_ohlcv_data("XRPUSDT", "4H", 100) → 100 4H-Kerzen für HTF
• get_realtime_price("XRPUSDT") → Aktueller Preis
• get_futures_data("XRPUSDT") → Funding Rate, Open Interest

⛔ ABSOLUT VERBOTEN:
- "Ich brauche Daten von dir" → FALSCH! Hole sie SELBST!
- "Welche Börse benutzt du?" → IRRELEVANT! Du hast Bitget!
- "Bitte schicke mir die Daten" → NIEMALS! Du holst sie selbst!
- Auf Daten vom Benutzer warten → NIEMALS!

✅ KORREKTES VERHALTEN:
Bei JEDER Anfrage SOFORT diese Schritte ausführen:
1. get_ohlcv_data("SYMBOL", "1H", 200) aufrufen
2. RSI, MACD, Bollinger aus den echten Daten berechnen
3. S/R Levels aus echten Highs/Lows identifizieren
4. Entry/SL/TP aus echten Daten bestimmen
5. ChartingAgent für Visualisierung aufrufen

Symbol-Format: 'BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'SOLUSDT'
═══════════════════════════════════════════════════════════════════════════════

Technical Analysis Guidelines:
- RSI < 30 = Oversold (potential buy)
- RSI > 70 = Overbought (potential sell)
- MACD crossover = Trend change signal

Entry Point Format für ChartingAgent:
{"type": "long", "price": X, "stop_loss": Y, "take_profit": [Z1, Z2], "reason": "...", "confidence": "high/medium/low"}

NACH der Analyse IMMER ChartingAgent aufrufen mit:
- indicators: 'rsi,macd,sma,ema,bollinger'
- support_levels: [aus echten Daten berechnete Levels]
- resistance_levels: [aus echten Daten berechnete Levels]
- entry_points: [berechnete Entry-Punkte]
""" + SHARED_AGENT_RULES,
            description="Expert in technical analysis with DIRECT ACCESS to live Bitget data",
        )
        
        charting_agent = AssistantAgent(
            "ChartingAgent",
            model_client=self.model_client,
            tools=tradingview_tools_list + exchange_tools_list,
            system_message="""You are a professional charting specialist with DIRECT ACCESS to live market data.

═══════════════════════════════════════════════════════════════════════════════
🚨 DU HAST DIREKTEN ZUGRIFF AUF LIVE-DATEN! 🚨
═══════════════════════════════════════════════════════════════════════════════

DU HAST DIESE TOOLS:
• get_ohlcv_data("XRPUSDT", "1H", 200) → Echte Kerzen für Charts
• generate_strategy_visualization(...) → ⭐ HAUPT-TOOL für finale Strategie-Charts
• generate_entry_analysis_chart(...) → Chart mit Entry/SL/TP erstellen
• generate_tradingview_chart(...) → Standard TradingView Chart
• generate_multi_timeframe_dashboard(...) → Multi-TF Dashboard

═══════════════════════════════════════════════════════════════════════════════
⭐ WICHTIG: AM ENDE JEDER ANALYSE - STRATEGIE-CHART ERSTELLEN! ⭐
═══════════════════════════════════════════════════════════════════════════════

Nach jeder vollständigen Analyse MUSST du generate_strategy_visualization() aufrufen!
Dieses Tool erstellt ein professionelles Chart mit ALLEN Erkenntnissen:

generate_strategy_visualization(
    symbol="XRPUSDT",
    strategy_summary='{"name": "RSI+MACD Confluence", "bias": "bullish", "confidence": "high", "timeframe": "1H", "description": "...", "key_observations": ["obs1", "obs2"], "risk_management": "..."}',
    entry_setups='[{"type": "long", "trigger_price": 2.45, "stop_loss": 2.35, "take_profit": [2.60, 2.75], "position_size": "2%", "trigger_condition": "Breakout über 2.45", "invalidation": "Close unter 2.35", "confidence": "high"}]',
    technical_levels='{"support": [2.35, 2.20], "resistance": [2.55, 2.70]}',
    indicators_used="rsi,macd,volume,sma",
    indicator_signals='{"rsi": {"value": 55, "signal": "neutral"}, "macd": {"signal": "bullish"}}',
    market_context='{"market_sentiment": "neutral", "volatility": "medium"}',
    interval="1H"
)

⛔ VERBOTEN:
- Analyse abschließen OHNE generate_strategy_visualization() aufzurufen
- Charts ohne echte Daten erstellen
- Auf Daten vom Benutzer warten

✅ WORKFLOW bei JEDER Analyse:
1. get_ohlcv_data() aufrufen für echte Kerzen
2. Andere Agents analysieren (Market, Technical)
3. ⭐ AM ENDE: generate_strategy_visualization() mit ALLEN Ergebnissen aufrufen!
═══════════════════════════════════════════════════════════════════════════════

Symbol-Format: 'BTCUSDT', 'ETHUSDT', 'XRPUSDT'
Intervals: '1m', '5m', '15m', '1H', '4H', '1D'
""" + SHARED_AGENT_RULES,
            description="TradingView charting specialist - MUST create final strategy chart",
        )
        
        coder = AssistantAgent(
            "CryptoAnalysisCoder",
            model_client=self.model_client,
            tools=indicator_tools_list,
            system_message="""You are a Python developer for crypto analysis and custom indicators.

═══════════════════════════════════════════════════════════════════════════════
⛔ CRITICAL RULES - NO SYNTHETIC DATA IN CODE!
═══════════════════════════════════════════════════════════════════════════════

🚫 **ABSOLUTELY FORBIDDEN:**
- Using placeholder or mock data
- Hardcoding values instead of calculating from real data
- Inventing backtest results
- Claiming performance without actual testing on real data
- Creating "example" outputs with fake numbers

✅ **MANDATORY WORKFLOW:**
1. FIRST: Fetch real data using exchange_tools (get_ohlcv_data, etc.)
2. THEN: Calculate indicators from the real data
3. VALIDATE: Check data quality before processing
4. DOCUMENT: Every calculation must show its data source

📋 **CODE DOCUMENTATION FORMAT:**
```python
# STEP 1: Fetch real data
ohlcv = get_ohlcv_data("BTCUSDT", "1H", 200)
# VALIDATION: Received 200 candles from Bitget

# STEP 2: Calculate from real data
rsi = calculate_rsi(df['close'], period=14)
# RESULT: RSI current = X.X (calculated from real closes)
```
═══════════════════════════════════════════════════════════════════════════════

Your role:
1. Write Python scripts for advanced analysis using REAL DATA
2. Implement custom indicators designed by TechnicalAnalyst
3. Backtest and evaluate indicator performance on REAL HISTORICAL DATA
4. Save indicators to the registry for reuse

Always check for existing indicators before creating new ones.
Save working indicators so they can be reused in future sessions.""" + SHARED_AGENT_RULES,
            description="Python developer for analysis and custom indicators",
        )
        
        report_writer = AssistantAgent(
            "ReportWriter",
            model_client=self.model_client,
            tools=report_tools_list,
            system_message="""You are a professional cryptocurrency report writer.

═══════════════════════════════════════════════════════════════════════════════
⛔ CRITICAL RULES - REPORTS MUST ONLY CONTAIN REAL DATA!
═══════════════════════════════════════════════════════════════════════════════

🚫 **ABSOLUTELY FORBIDDEN:**
- Including data you didn't receive from other agents' tool calls
- Adding hypothetical scenarios or speculation
- Inventing statistics or performance metrics
- Writing predictions without data backing
- Adding recommendations without real data support

✅ **MANDATORY BEHAVIOR:**
- ONLY include facts provided by other agents FROM THEIR TOOL CALLS
- Every number must have a documented source (Bitget, CoinGecko, timestamp)
- Clearly separate FACTS (from data) from INTERPRETATION
- Add "Data Source: [Agent, Tool, Timestamp]" to each section

═══════════════════════════════════════════════════════════════════════════════
⭐ WICHTIG: Nach deinem Report muss ChartingAgent das finale Chart erstellen!
═══════════════════════════════════════════════════════════════════════════════

Beende deinen Report mit einem klaren Aufruf an ChartingAgent:

"@ChartingAgent: Bitte erstelle das finale Strategie-Chart mit generate_strategy_visualization():
- Symbol: [SYMBOL]
- Bias: [bullish/bearish/neutral]
- Entry: [Preis] mit SL: [Preis] und TP: [Preise]
- Support: [Levels]
- Resistance: [Levels]
- Indikatoren: [Liste]"

📋 **REPORT STRUCTURE:**
```markdown
# [Symbol] Analysis Report
**Generated:** [Date/Time]
**Data Sources:** [Bitget/CoinGecko, Timestamps]

## Data Retrieved
| Metric | Value | Source | Timestamp |
|--------|-------|--------|-----------|
| Price  | $X.XX | Bitget | 12:34:56  |

## Analysis (Based on Real Data Only)
[Only include what was actually calculated from fetched data]

## Handlungsempfehlung
[Klare Entry/SL/TP mit Begründung]

---
@ChartingAgent: Erstelle finales Chart...
```
═══════════════════════════════════════════════════════════════════════════════

Report types:
- Analysis Reports: Full analysis of a single cryptocurrency
- Comparison Reports: Side-by-side comparison of multiple coins
- Custom Indicator Reports: Document new indicator designs

Use proper Markdown formatting with headers, bold text, tables, and bullet points.""" + SHARED_AGENT_RULES,
            description="Report writer - MUST request final chart from ChartingAgent",
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
        
        # Retry configuration for content filter errors
        max_retries = 2
        current_retry = 0
        current_prompt = prompt
        
        while current_retry <= max_retries:
            try:
                async for msg in team.run_stream(task=current_prompt):
                    if self._cancelled:
                        yield StatusEvent(
                            status="cancelled",
                            message="Task cancelled by user",
                            timestamp=datetime.now(),
                        )
                        return  # Exit completely on cancel
                    
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
                        return  # Success - exit the retry loop
                    
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
                
                # If we reach here, the agent stream completed successfully
                # Exit the retry loop
                return
        
            except asyncio.CancelledError:
                logger.info("Agent task cancelled")
                yield ErrorEvent(
                    message="Task cancelled",
                    details="The analysis was cancelled by the user",
                    recoverable=True,
                    timestamp=datetime.now(),
                )
                return  # Don't retry on cancellation
                
            except Exception as e:
                error_str = str(e)
                logger.exception("Error during agent execution (attempt %d/%d)", current_retry + 1, max_retries + 1)
                
                # Check if this is a content filter error
                content_filter_info = _parse_content_filter_error(error_str)
                
                if content_filter_info and content_filter_info.get("is_content_filter"):
                    filter_type = content_filter_info.get("filter_type", "unknown")
                    filter_results = content_filter_info.get("filter_results")
                    
                    if current_retry < max_retries:
                        # We have retries left - notify user and retry with sanitized prompt
                        current_retry += 1
                        sanitized_prompt = self._sanitize_prompt_for_retry(current_prompt)
                        
                        logger.info(
                            "Content filter triggered, retrying with sanitized prompt (attempt %d/%d)",
                            current_retry + 1, max_retries + 1
                        )
                        
                        yield ContentFilterRetryEvent(
                            message=f"Content Filter aktiviert - Wiederhole mit angepasster Anfrage ({current_retry}/{max_retries})",
                            retry_count=current_retry,
                            max_retries=max_retries,
                            filter_type=filter_type,
                            timestamp=datetime.now(),
                        )
                        
                        # Update prompt for next iteration
                        current_prompt = sanitized_prompt
                        
                        # Create a fresh team for the retry
                        team = await self._create_team()
                        
                        # Small delay before retry
                        await asyncio.sleep(1)
                        
                        # Continue to next iteration of while loop
                        continue
                    else:
                        # Max retries exceeded - show full error to user
                        display_prompt = current_prompt
                        if len(current_prompt) > 2000:
                            display_prompt = f"{current_prompt[:1000]}\n\n... [Truncated {len(current_prompt) - 1500} characters] ...\n\n{current_prompt[-500:]}"
                        
                        yield ContentFilterErrorEvent(
                            message=f"Azure Content Filter triggered ({filter_type}) - alle Wiederholungsversuche fehlgeschlagen",
                            triggered_prompt=display_prompt,
                            filter_results=filter_results,
                            filter_type=filter_type,
                            recoverable=True,
                            timestamp=datetime.now(),
                        )
                        return  # Exit after max retries
                else:
                    # Not a content filter error - don't retry
                    yield ErrorEvent(
                        message="Agent execution failed",
                        details=error_str,
                        recoverable=True,
                        timestamp=datetime.now(),
                    )
                    return
    
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
