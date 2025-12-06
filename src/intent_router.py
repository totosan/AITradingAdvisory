"""
Intent Detection and Routing for Crypto Analysis Platform

This module provides intelligent intent classification using a fast LLM call,
with pattern-based fallback for reliability.

Intent Types:
- SIMPLE_LOOKUP: Direct tool call (price, basic info) - fast, no agents needed
- ANALYSIS: Full multi-agent analysis required
- CHART: Chart generation request
- REPORT: Report generation request
- COMPARISON: Compare multiple assets
- CONVERSATION: Follow-up or clarification

Usage:
    router = IntentRouter(model_client)
    intent = await router.classify_async(user_message)  # LLM-based
    intent = router.classify(user_message)  # Pattern-based fallback
    
    if intent.type == IntentType.SIMPLE_LOOKUP:
        result = await router.execute_simple(user_message, intent)
    else:
        # Use full AITradingAdvisory team
        ...
"""
import re
import json
import logging
from enum import Enum
from typing import Optional, Dict, Any, List, Callable, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Types of user intents."""
    SIMPLE_LOOKUP = "simple_lookup"      # Direct data fetch, single tool call
    ANALYSIS = "analysis"                 # Full multi-agent analysis needed
    CHART = "chart"                       # Chart generation request
    REPORT = "report"                     # Report generation request  
    COMPARISON = "comparison"             # Compare multiple assets
    CONVERSATION = "conversation"         # Follow-up, clarification, general chat


# Mapping from string to IntentType for LLM responses
INTENT_TYPE_MAP = {
    "simple_lookup": IntentType.SIMPLE_LOOKUP,
    "price": IntentType.SIMPLE_LOOKUP,  # Alias
    "lookup": IntentType.SIMPLE_LOOKUP,  # Alias
    "analysis": IntentType.ANALYSIS,
    "analyze": IntentType.ANALYSIS,  # Alias
    "chart": IntentType.CHART,
    "report": IntentType.REPORT,
    "comparison": IntentType.COMPARISON,
    "compare": IntentType.COMPARISON,  # Alias
    "conversation": IntentType.CONVERSATION,
    "chat": IntentType.CONVERSATION,  # Alias
}


@dataclass
class Intent:
    """
    Represents a classified user intent.
    
    Supports compound queries via sub_intents - e.g., "price of BTC and show chart"
    would have primary_type=CHART with sub_intents=[SIMPLE_LOOKUP] so we can
    show the price immediately while the chart is being generated.
    """
    type: IntentType
    confidence: float  # 0.0 to 1.0
    entities: Dict[str, Any] = field(default_factory=dict)  # Extracted entities (symbols, etc.)
    tool_hint: Optional[str] = None  # Suggested tool for SIMPLE_LOOKUP
    reason: str = ""  # Why this classification was made
    sub_intents: List[IntentType] = field(default_factory=list)  # Secondary intents that can be pre-executed
    
    def is_simple(self) -> bool:
        """Check if this intent can be handled with a simple tool call."""
        return self.type == IntentType.SIMPLE_LOOKUP and self.confidence >= 0.7
    
    def has_quick_component(self) -> bool:
        """
        Check if this compound intent has a quick lookup component.
        
        Returns True if SIMPLE_LOOKUP is in sub_intents, meaning we can
        show quick data while processing the main (complex) intent.
        """
        return IntentType.SIMPLE_LOOKUP in self.sub_intents
    
    def is_compound(self) -> bool:
        """Check if this is a compound intent with multiple components."""
        return len(self.sub_intents) > 0


# Intent classification prompt - designed for fast, accurate classification with decomposition
INTENT_CLASSIFICATION_PROMPT = '''You are an intent classifier for a cryptocurrency analysis platform.

Classify the user's message into a PRIMARY intent and optional SECONDARY intents for compound queries.

Primary intents (pick the MAIN goal):
- **simple_lookup**: User ONLY wants quick data (price, basic info). Examples: "What's the price of BTC?", "How much is ETH?"
- **analysis**: User wants in-depth analysis, trends, signals, recommendations. Examples: "Analyze BTC", "What's the situation with ETH?"
- **chart**: User wants a chart or visualization. Examples: "Create a chart for BTC", "Show me a dashboard"
- **comparison**: User wants to compare assets. Examples: "Compare BTC vs ETH", "Which is better?"
- **report**: User wants a written report. Examples: "Write a report on BTC"
- **conversation**: General questions, follow-ups. Examples: "Thanks", "What do you mean?"

For COMPOUND queries (e.g., "What is the price of BTC and show me a chart?"), identify:
1. The PRIMARY intent (the main deliverable - e.g., "chart")
2. Any SECONDARY intents that can be answered quickly first (e.g., "simple_lookup" for price)

Also extract cryptocurrency symbols (BTC, ETH, SOL, SUI, XRP, ADA, DOGE, AVAX, DOT, MATIC, LINK, etc.).

Respond ONLY with valid JSON:
{"intent": "<primary_intent>", "sub_intents": ["<secondary_intent>"], "symbols": ["SYM1"], "confidence": 0.9, "reason": "explanation"}

Examples:
- "BTC price" -> {"intent": "simple_lookup", "sub_intents": [], "symbols": ["BTC"], "confidence": 0.95, "reason": "Simple price query"}
- "Price of BTC and create a chart" -> {"intent": "chart", "sub_intents": ["simple_lookup"], "symbols": ["BTC"], "confidence": 0.9, "reason": "Chart request with price component"}
- "Analyze ETH and show current price" -> {"intent": "analysis", "sub_intents": ["simple_lookup"], "symbols": ["ETH"], "confidence": 0.9, "reason": "Analysis with price lookup"}

User message: '''


class IntentRouter:
    """
    Routes user queries to appropriate handlers based on intent.
    
    Uses LLM for smart classification with pattern-based fallback.
    """
    
    def __init__(self, model_client=None, use_llm: bool = True):
        """
        Initialize the intent router.
        
        Args:
            model_client: Optional LLM client for smart classification.
                         If None, will try to create one from config.
            use_llm: Whether to use LLM for classification (default True).
                    Falls back to patterns if False or LLM unavailable.
        """
        self.tools: Dict[str, Callable] = {}
        self._model_client = model_client
        self._use_llm = use_llm
        self._llm_initialized = False
        
        # Known crypto symbols for extraction
        self._known_symbols = {
            "BTC", "ETH", "SOL", "SUI", "XRP", "ADA", "DOGE", "AVAX", 
            "DOT", "MATIC", "LINK", "UNI", "ATOM", "LTC", "BCH", "NEAR",
            "APT", "ARB", "OP", "INJ", "TIA", "SEI", "MEME", "PEPE",
            "SHIB", "BNB", "TON", "TRX", "HBAR", "FIL", "AAVE", "MKR",
        }
        
        # Full name to symbol mapping
        self._name_to_symbol = {
            "BITCOIN": "BTC", "ETHEREUM": "ETH", "SOLANA": "SOL",
            "RIPPLE": "XRP", "CARDANO": "ADA", "DOGECOIN": "DOGE",
            "AVALANCHE": "AVAX", "POLKADOT": "DOT", "POLYGON": "MATIC",
            "CHAINLINK": "LINK", "UNISWAP": "UNI", "COSMOS": "ATOM",
            "LITECOIN": "LTC", "APTOS": "APT", "ARBITRUM": "ARB",
            "OPTIMISM": "OP", "INJECTIVE": "INJ", "CELESTIA": "TIA",
        }
    
    def _get_model_client(self):
        """Get or create the model client for LLM classification."""
        if self._model_client is not None:
            return self._model_client
        
        if self._llm_initialized:
            return None
        
        self._llm_initialized = True
        
        try:
            # Try multiple import paths for flexibility
            try:
                from src.config import AppConfig
            except ImportError:
                from config import AppConfig
            
            from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
            
            config = AppConfig.from_env()
            
            # Use the configured model for intent classification
            model_info = {
                "vision": False,
                "function_calling": False,
                "json_output": True,
                "family": "gpt-4",
            }
            
            self._model_client = AzureOpenAIChatCompletionClient(
                azure_deployment=config.azure_openai.deployment,
                api_version=config.azure_openai.api_version,
                azure_endpoint=config.azure_openai.endpoint,
                api_key=config.azure_openai.api_key,
                model=config.azure_openai.model_name,
                model_info=model_info,
            )
            logger.info("LLM intent classifier initialized")
            return self._model_client
            
        except Exception as e:
            logger.warning(f"Could not initialize LLM for intent classification: {e}")
            return None
    
    def _extract_symbols(self, text: str) -> List[str]:
        """Extract cryptocurrency symbols from text."""
        text_upper = text.upper()
        found = []
        
        # Check for known symbols
        for sym in self._known_symbols:
            if re.search(rf'\b{sym}\b', text_upper):
                found.append(f"{sym}USDT")
        
        # Check for full names
        for name, sym in self._name_to_symbol.items():
            if re.search(rf'\b{name}\b', text_upper):
                symbol = f"{sym}USDT"
                if symbol not in found:
                    found.append(symbol)
        
        return found
    
    async def _classify_with_llm(self, message: str) -> Optional[Intent]:
        """
        Classify intent using LLM.
        
        Returns None if LLM is unavailable or fails.
        """
        client = self._get_model_client()
        if client is None:
            return None
        
        try:
            from autogen_core.models import UserMessage
            
            prompt = INTENT_CLASSIFICATION_PROMPT + message
            
            response = await client.create(
                messages=[UserMessage(content=prompt, source="user")],
                json_output=True,
            )
            
            # Parse LLM response
            content = response.content
            if isinstance(content, str):
                # Try to extract JSON from response
                json_match = re.search(r'\{[^{}]*\}', content)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    data = json.loads(content)
            else:
                data = content
            
            # Map intent string to IntentType
            intent_str = data.get("intent", "conversation").lower()
            intent_type = INTENT_TYPE_MAP.get(intent_str, IntentType.CONVERSATION)
            
            # Extract sub_intents for compound queries
            sub_intent_strs = data.get("sub_intents", [])
            sub_intents = []
            for sub_str in sub_intent_strs:
                sub_type = INTENT_TYPE_MAP.get(sub_str.lower())
                if sub_type and sub_type != intent_type:
                    sub_intents.append(sub_type)
            
            # Extract symbols from LLM response, normalize to USDT pairs
            llm_symbols = data.get("symbols", [])
            symbols = []
            for sym in llm_symbols:
                sym_upper = sym.upper().replace("USDT", "")
                if sym_upper in self._known_symbols:
                    symbols.append(f"{sym_upper}USDT")
                elif sym_upper in self._name_to_symbol:
                    symbols.append(f"{self._name_to_symbol[sym_upper]}USDT")
            
            # Also extract from original message in case LLM missed some
            msg_symbols = self._extract_symbols(message)
            for s in msg_symbols:
                if s not in symbols:
                    symbols.append(s)
            
            confidence = float(data.get("confidence", 0.85))
            reason = data.get("reason", "LLM classification")
            
            # Determine tool hint for simple lookups (primary or sub-intent)
            tool_hint = None
            if intent_type == IntentType.SIMPLE_LOOKUP or IntentType.SIMPLE_LOOKUP in sub_intents:
                tool_hint = "get_realtime_price"
            
            # Log compound intent detection
            if sub_intents:
                sub_names = [s.value for s in sub_intents]
                logger.info(f"LLM classified '{message[:50]}...' as {intent_type.value} with sub-intents {sub_names}")
            else:
                logger.info(f"LLM classified '{message[:50]}...' as {intent_type.value} (conf: {confidence:.2f})")
            
            return Intent(
                type=intent_type,
                confidence=confidence,
                entities={"symbols": symbols},
                tool_hint=tool_hint,
                reason=f"LLM: {reason}",
                sub_intents=sub_intents,
            )
            
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")
            return None
    
    def _classify_with_patterns(self, message: str) -> Intent:
        """
        Fallback pattern-based classification.
        
        Used when LLM is unavailable or as a sanity check.
        Supports compound query detection via sub_intents.
        """
        message_lower = message.lower().strip()
        symbols = self._extract_symbols(message)
        entities = {"symbols": symbols}
        sub_intents = []
        
        # Empty message
        if not message_lower:
            return Intent(
                type=IntentType.CONVERSATION,
                confidence=1.0,
                entities=entities,
                reason="Empty message"
            )
        
        # Detect compound queries - check for multiple intent signals
        has_price_component = any(t in message_lower for t in ["price", "how much", "cost"])
        has_chart_component = any(t in message_lower for t in ["chart", "graph", "dashboard", "visuali"])
        has_analysis_component = any(t in message_lower for t in [
            "analyze", "analysis", "situation", "outlook", "trend", 
            "recommend", "should i", "what do you think"
        ])
        has_report_component = any(t in message_lower for t in ["report", "document", "write up"])
        has_comparison_component = any(t in message_lower for t in [" vs ", " versus ", "compare"])
        
        # Count how many intent components are present
        components = [
            (has_price_component, IntentType.SIMPLE_LOOKUP),
            (has_chart_component, IntentType.CHART),
            (has_analysis_component, IntentType.ANALYSIS),
            (has_report_component, IntentType.REPORT),
            (has_comparison_component, IntentType.COMPARISON),
        ]
        active_components = [(present, intent) for present, intent in components if present]
        
        # If compound query detected (2+ components), determine primary and sub-intents
        if len(active_components) >= 2:
            # Priority order: ANALYSIS > CHART > REPORT > COMPARISON > SIMPLE_LOOKUP
            priority_order = [
                IntentType.ANALYSIS, IntentType.CHART, IntentType.REPORT, 
                IntentType.COMPARISON, IntentType.SIMPLE_LOOKUP
            ]
            
            detected_intents = [intent for _, intent in active_components]
            primary_type = None
            
            for p_type in priority_order:
                if p_type in detected_intents:
                    primary_type = p_type
                    break
            
            # All other detected intents become sub-intents
            sub_intents = [i for i in detected_intents if i != primary_type]
            
            # Ensure SIMPLE_LOOKUP is first in sub_intents if present (for quick execution)
            if IntentType.SIMPLE_LOOKUP in sub_intents:
                sub_intents.remove(IntentType.SIMPLE_LOOKUP)
                sub_intents.insert(0, IntentType.SIMPLE_LOOKUP)
            
            tool_hint = "get_realtime_price" if IntentType.SIMPLE_LOOKUP in sub_intents else None
            
            return Intent(
                type=primary_type,
                confidence=0.8,
                entities=entities,
                tool_hint=tool_hint,
                reason=f"Compound query: {primary_type.value} with {[s.value for s in sub_intents]}",
                sub_intents=sub_intents,
            )
        
        # Simple price patterns (high confidence) - only if JUST price
        simple_patterns = [
            r"^what(?:'s| is) the (?:current )?price",
            r"^(?:get|show|check) (?:the )?price",
            r"^how much (?:is|does)",
            r"^price of\b",
            r"^\w+ price\??$",
            r"^(?:current )?price",
        ]
        
        for pattern in simple_patterns:
            if re.search(pattern, message_lower):
                # Make sure it's not also asking for analysis/chart/etc
                if not any(t in message_lower for t in ["analyze", "analysis", "trend", "signal", "recommend", "chart", "graph"]):
                    return Intent(
                        type=IntentType.SIMPLE_LOOKUP,
                        confidence=0.85,
                        entities=entities,
                        tool_hint="get_realtime_price",
                        reason="Matches simple price pattern"
                    )
        
        # Analysis triggers
        analysis_triggers = [
            "analyze", "analysis", "analyse", "situation", "outlook",
            "forecast", "trend", "momentum", "signal", "recommend",
            "should i buy", "should i sell", "entry", "exit",
            "support", "resistance", "technical", "what do you think",
        ]
        if any(t in message_lower for t in analysis_triggers):
            return Intent(
                type=IntentType.ANALYSIS,
                confidence=0.85,
                entities=entities,
                reason="Contains analysis triggers"
            )
        
        # Comparison triggers (check before chart triggers)
        comparison_triggers = [
            " vs ", " versus ", "compare", "comparison", 
            "better than", "which is better", "difference between",
        ]
        if any(t in message_lower for t in comparison_triggers):
            return Intent(
                type=IntentType.COMPARISON,
                confidence=0.85,
                entities=entities,
                reason="Contains comparison triggers"
            )
        
        # Chart triggers
        if any(t in message_lower for t in ["chart", "graph", "dashboard", "visuali"]):
            return Intent(
                type=IntentType.CHART,
                confidence=0.85,
                entities=entities,
                reason="Contains chart triggers"
            )
        
        # Report triggers
        if any(t in message_lower for t in ["report", "document", "write up"]):
            return Intent(
                type=IntentType.REPORT,
                confidence=0.85,
                entities=entities,
                reason="Contains report triggers"
            )
        
        # Short message with symbols -> likely simple lookup
        if symbols and len(message.split()) <= 6:
            return Intent(
                type=IntentType.SIMPLE_LOOKUP,
                confidence=0.7,
                entities=entities,
                tool_hint="get_realtime_price",
                reason="Short message with crypto symbols"
            )
        
        # Default to analysis for anything with crypto symbols
        if symbols:
            return Intent(
                type=IntentType.ANALYSIS,
                confidence=0.6,
                entities=entities,
                reason="Contains crypto symbols, defaulting to analysis"
            )
        
        # Default fallback
        return Intent(
            type=IntentType.CONVERSATION,
            confidence=0.5,
            entities=entities,
            reason="No specific pattern matched"
        )
    
    async def classify_async(self, message: str) -> Intent:
        """
        Classify the user's intent using LLM with pattern fallback.
        
        This is the async version that uses the LLM.
        
        Args:
            message: The user's message
            
        Returns:
            Intent object with classification and metadata
        """
        # Try LLM classification first
        if self._use_llm:
            llm_intent = await self._classify_with_llm(message)
            if llm_intent is not None:
                return llm_intent
        
        # Fallback to pattern-based
        pattern_intent = self._classify_with_patterns(message)
        logger.debug(f"Pattern classified as: {pattern_intent.type.value}")
        return pattern_intent
    
    def classify(self, message: str) -> Intent:
        """
        Synchronous classification using patterns only.
        
        For async LLM classification, use classify_async().
        
        Args:
            message: The user's message
            
        Returns:
            Intent object with classification and metadata
        """
        return self._classify_with_patterns(message)
    
    async def execute_simple(
        self,
        message: str,
        intent: Intent,
        tools: Optional[Dict[str, Callable]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a simple lookup without the full agent team.
        
        Supports multiple symbols - will fetch data for all symbols found.
        
        Args:
            message: Original user message
            intent: Classified intent
            tools: Dict of available tools (tool_name -> async function)
            
        Returns:
            Dict with result and metadata
        """
        tools = tools or self.tools
        
        if not intent.is_simple():
            return {
                "success": False,
                "error": "Intent is not classified as simple lookup",
                "fallback_to_agents": True,
            }
        
        symbols = intent.entities.get("symbols", [])
        if not symbols:
            return {
                "success": False,
                "error": "No cryptocurrency symbol found in message",
                "fallback_to_agents": True,
            }
        
        tool_name = intent.tool_hint or "get_realtime_price"
        
        if tool_name not in tools:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not available",
                "fallback_to_agents": True,
            }
        
        tool_func = tools[tool_name]
        results = []
        errors = []
        
        # Fetch data for ALL symbols found
        for symbol in symbols:
            try:
                import asyncio
                if asyncio.iscoroutinefunction(tool_func):
                    result = await tool_func(symbol)
                else:
                    result = tool_func(symbol)
                
                results.append({
                    "symbol": symbol,
                    "data": result,
                })
            except Exception as e:
                errors.append({
                    "symbol": symbol,
                    "error": str(e),
                })
        
        if not results and errors:
            return {
                "success": False,
                "error": f"Failed to fetch data: {errors[0]['error']}",
                "fallback_to_agents": True,
            }
        
        return {
            "success": True,
            "results": results,
            "errors": errors,
            "tool_used": tool_name,
            "symbols": symbols,
            "intent_type": intent.type.value,
            "confidence": intent.confidence,
        }
    
    def register_tool(self, name: str, func: Callable) -> None:
        """Register a tool for simple execution."""
        self.tools[name] = func
    
    def set_model_client(self, client) -> None:
        """Set the model client for LLM classification."""
        self._model_client = client
        self._llm_initialized = True


def format_simple_result(result: Dict[str, Any]) -> str:
    """
    Format a simple lookup result for display.
    
    Handles both single and multiple symbol results.
    
    Args:
        result: Result from execute_simple()
        
    Returns:
        Formatted string for user display
    """
    if not result.get("success"):
        return f"❌ {result.get('error', 'Unknown error')}"
    
    # Handle multiple results (new format)
    if "results" in result:
        lines = []
        for item in result["results"]:
            symbol = item.get("symbol", "")
            data = item.get("data", "")
            formatted = _format_single_price(symbol, data)
            lines.append(formatted)
        
        # Add any errors
        for err in result.get("errors", []):
            lines.append(f"❌ **{err['symbol']}**: {err['error']}")
        
        return "\n".join(lines)
    
    # Legacy single result format (for backward compatibility)
    tool_result = result.get("result", "")
    symbol = result.get("symbol", "")
    return _format_single_price(symbol, tool_result)


def _format_price(price: float) -> str:
    """
    Format a price with appropriate decimal places.
    
    Uses 4 decimal places for small prices (< $1),
    2 decimal places for larger prices.
    """
    if price < 0.01:
        return f"${price:,.6f}"
    elif price < 1:
        return f"${price:,.4f}"
    else:
        return f"${price:,.4f}"


def _format_single_price(symbol: str, data: Any) -> str:
    """Format a single price result."""
    try:
        if isinstance(data, str):
            parsed = json.loads(data)
        else:
            parsed = data
            
        if isinstance(parsed, dict):
            price = parsed.get("price") or parsed.get("current_price")
            change_24h = parsed.get("change_24h") or parsed.get("price_change_24h")
            
            if price:
                if isinstance(price, (int, float)):
                    output = f"💰 **{symbol}**: {_format_price(float(price))}"
                else:
                    output = f"💰 **{symbol}**: {price}"
                
                if change_24h is not None:
                    try:
                        change_val = float(change_24h)
                        emoji = "📈" if change_val > 0 else "📉"
                        output += f" ({emoji} {change_val:+.2f}%)"
                    except (ValueError, TypeError):
                        output += f" ({change_24h})"
                
                return output
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    
    # Fallback to raw result
    return f"💰 **{symbol}**: {data}" if symbol else str(data)
