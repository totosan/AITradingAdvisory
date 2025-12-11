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

Asset Types:
- CRYPTO: Cryptocurrency (BTC, ETH, etc.) - routes to Bitget/CoinGecko
- STOCK: Stocks/ETFs (AAPL, MSFT, etc.) - routes to Yahoo Finance
- UNKNOWN: Could not determine asset type

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


class AssetType(Enum):
    """Asset type for provider routing."""
    CRYPTO = "crypto"                     # Cryptocurrency (BTC, ETH, etc.)
    STOCK = "stock"                       # Stocks/ETFs (AAPL, MSFT, etc.)
    UNKNOWN = "unknown"                   # Could not determine


class StrategyType(Enum):
    """
    Trading strategy types for prediction categorization.
    
    Used to isolate feedback loops - e.g., Range trading feedback
    doesn't affect Breakout-Pullback performance metrics.
    """
    RANGE = "range"                      # Range/channel trading
    BREAKOUT_PULLBACK = "breakout_pullback"  # Breakout with pullback entry
    TREND_FOLLOWING = "trend_following"  # Trend/momentum trading
    REVERSAL = "reversal"                # Counter-trend reversals
    SCALPING = "scalping"                # Short-term scalping
    UNKNOWN = "unknown"                  # Could not classify


# Keywords for strategy classification
STRATEGY_KEYWORDS: Dict[StrategyType, List[str]] = {
    StrategyType.RANGE: [
        "range", "seitwärts", "sideways", "channel", "consolidation",
        "konsolidierung", "bounce", "support resistance", "s/r",
        "range-bound", "ranging", "box", "rectangle",
    ],
    StrategyType.BREAKOUT_PULLBACK: [
        "breakout", "ausbruch", "pullback", "retest", "break out",
        "durchbruch", "rücksetzer", "false breakout", "fakeout",
        "break and retest", "continuation", "expansion",
    ],
    StrategyType.TREND_FOLLOWING: [
        "trend", "momentum", "ema cross", "ma cross", "moving average",
        "gleitender durchschnitt", "trend following", "with the trend",
        "higher high", "lower low", "impulse", "swing",
    ],
    StrategyType.REVERSAL: [
        "reversal", "umkehr", "divergence", "divergenz", "oversold",
        "overbought", "überkauft", "überverkauft", "bottom", "top",
        "double top", "double bottom", "head and shoulders",
        "erschöpfung", "exhaustion", "counter-trend",
    ],
    StrategyType.SCALPING: [
        "scalp", "scalping", "quick", "short-term", "kurzfristig",
        "5m", "15m", "1m", "fast trade", "schnell", "intraday",
        "day trade", "daytrade",
    ],
}

# Mapping from string to StrategyType for LLM responses
STRATEGY_TYPE_MAP = {
    "range": StrategyType.RANGE,
    "breakout_pullback": StrategyType.BREAKOUT_PULLBACK,
    "breakout": StrategyType.BREAKOUT_PULLBACK,  # Alias
    "pullback": StrategyType.BREAKOUT_PULLBACK,  # Alias
    "trend_following": StrategyType.TREND_FOLLOWING,
    "trend": StrategyType.TREND_FOLLOWING,  # Alias
    "momentum": StrategyType.TREND_FOLLOWING,  # Alias
    "reversal": StrategyType.REVERSAL,
    "scalping": StrategyType.SCALPING,
    "scalp": StrategyType.SCALPING,  # Alias
    "unknown": StrategyType.UNKNOWN,
}


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
    
    Asset type classification is used to route to the correct data provider:
    - CRYPTO: Routes to Bitget (primary) or CoinGecko (fallback)
    - STOCK: Routes to Yahoo Finance
    """
    type: IntentType
    confidence: float  # 0.0 to 1.0
    entities: Dict[str, Any] = field(default_factory=dict)  # Extracted entities (symbols, etc.)
    tool_hint: Optional[str] = None  # Suggested tool for SIMPLE_LOOKUP
    reason: str = ""  # Why this classification was made
    sub_intents: List[IntentType] = field(default_factory=list)  # Secondary intents that can be pre-executed
    asset_type: AssetType = AssetType.UNKNOWN  # Detected asset type for routing
    
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
    
    def is_crypto(self) -> bool:
        """Check if this intent is for cryptocurrency assets."""
        return self.asset_type == AssetType.CRYPTO
    
    def is_stock(self) -> bool:
        """Check if this intent is for stock market assets."""
        return self.asset_type == AssetType.STOCK


# Intent classification prompt - designed for fast, accurate classification with decomposition
INTENT_CLASSIFICATION_PROMPT = '''You are an intent classifier for a financial analysis platform supporting both cryptocurrencies and stocks.

Classify the user's message into a PRIMARY intent, optional SECONDARY intents, and detect the ASSET TYPE.

Primary intents (pick the MAIN goal):
- **simple_lookup**: User ONLY wants quick data (price, basic info). Examples: "What's the price of BTC?", "AAPL price?"
- **analysis**: User wants in-depth analysis, trends, signals, recommendations. Examples: "Analyze BTC", "What's the situation with NVDA?"
- **chart**: User wants a chart or visualization. Examples: "Create a chart for BTC", "Show me AAPL chart"
- **comparison**: User wants to compare assets. Examples: "Compare BTC vs ETH", "AAPL vs MSFT"
- **report**: User wants a written report. Examples: "Write a report on BTC"
- **conversation**: General questions, follow-ups. Examples: "Thanks", "What do you mean?"

Asset types:
- **crypto**: Cryptocurrencies (BTC, ETH, SOL, XRP, DOGE, etc.) - uses Bitget/CoinGecko
- **stock**: Stocks, ETFs, indices (AAPL, MSFT, NVDA, SPY, ^GSPC, DAX, etc.) - uses Yahoo Finance
- **unknown**: Cannot determine

For COMPOUND queries (e.g., "What is the price of BTC and show me a chart?"), identify:
1. The PRIMARY intent (the main deliverable - e.g., "chart")
2. Any SECONDARY intents that can be answered quickly first (e.g., "simple_lookup" for price)

Extract symbols:
- Crypto: BTC, ETH, SOL, SUI, XRP, ADA, DOGE, AVAX, DOT, MATIC, LINK, etc.
- Stocks: AAPL, MSFT, GOOGL, NVDA, TSLA, AMZN, META, etc.
- German stocks: SAP, SIE, BMW, VOW3, BAYN, ALV, etc.
- Indices: ^GSPC (S&P 500), ^DJI (Dow Jones), ^GDAXI (DAX)

Respond ONLY with valid JSON:
{"intent": "<primary_intent>", "sub_intents": ["<secondary_intent>"], "symbols": ["SYM1"], "asset_type": "crypto|stock|unknown", "confidence": 0.9, "reason": "explanation"}

Examples:
- "BTC price" -> {"intent": "simple_lookup", "sub_intents": [], "symbols": ["BTC"], "asset_type": "crypto", "confidence": 0.95, "reason": "Crypto price query"}
- "AAPL stock price" -> {"intent": "simple_lookup", "sub_intents": [], "symbols": ["AAPL"], "asset_type": "stock", "confidence": 0.95, "reason": "Stock price query"}
- "Analyze NVDA" -> {"intent": "analysis", "sub_intents": [], "symbols": ["NVDA"], "asset_type": "stock", "confidence": 0.9, "reason": "Stock analysis"}
- "Compare BTC vs ETH" -> {"intent": "comparison", "sub_intents": [], "symbols": ["BTC", "ETH"], "asset_type": "crypto", "confidence": 0.9, "reason": "Crypto comparison"}

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
        self._known_crypto_symbols = {
            "BTC", "ETH", "SOL", "SUI", "XRP", "ADA", "DOGE", "AVAX", 
            "DOT", "MATIC", "LINK", "UNI", "ATOM", "LTC", "BCH", "NEAR",
            "APT", "ARB", "OP", "INJ", "TIA", "SEI", "MEME", "PEPE",
            "SHIB", "BNB", "TON", "TRX", "HBAR", "FIL", "AAVE", "MKR",
            "BONK", "WIF", "FTM", "ALGO", "XLM", "VET", "EGLD", "SAND",
            "MANA", "AXS", "GALA", "ENJ", "FLOW", "THETA", "GRT", "RNDR",
        }
        
        # Known stock symbols for extraction
        self._known_stock_symbols = {
            # US Tech Giants
            "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA",
            "AMD", "INTC", "CRM", "ORCL", "IBM", "CSCO", "ADBE", "NFLX",
            # US Finance
            "JPM", "BAC", "WFC", "GS", "MS", "V", "MA", "PYPL",
            # US Industrial & Consumer
            "DIS", "NKE", "MCD", "KO", "PEP", "WMT", "HD", "BA", "CAT",
            # German Stocks (base symbols)
            "SAP", "SIE", "ALV", "DTE", "BAYN", "BMW", "MBG", "VOW3",
            "ADS", "BAS", "DB1", "DBK", "DPW", "FRE", "HEI", "IFX",
            # ETFs
            "SPY", "QQQ", "DIA", "IWM", "VTI", "VOO", "ARKK", "XLF", "XLE",
        }
        
        # Crypto full name to symbol mapping
        self._crypto_name_to_symbol = {
            "BITCOIN": "BTC", "ETHEREUM": "ETH", "SOLANA": "SOL",
            "RIPPLE": "XRP", "CARDANO": "ADA", "DOGECOIN": "DOGE",
            "AVALANCHE": "AVAX", "POLKADOT": "DOT", "POLYGON": "MATIC",
            "CHAINLINK": "LINK", "UNISWAP": "UNI", "COSMOS": "ATOM",
            "LITECOIN": "LTC", "APTOS": "APT", "ARBITRUM": "ARB",
            "OPTIMISM": "OP", "INJECTIVE": "INJ", "CELESTIA": "TIA",
        }
        
        # Stock full name to symbol mapping
        self._stock_name_to_symbol = {
            "APPLE": "AAPL", "MICROSOFT": "MSFT", "GOOGLE": "GOOGL",
            "ALPHABET": "GOOGL", "AMAZON": "AMZN", "FACEBOOK": "META",
            "NVIDIA": "NVDA", "TESLA": "TSLA", "NETFLIX": "NFLX",
            "DISNEY": "DIS", "COCA-COLA": "KO", "PEPSI": "PEP",
            "MCDONALDS": "MCD", "NIKE": "NKE", "WALMART": "WMT",
            "BOEING": "BA", "VISA": "V", "MASTERCARD": "MA",
            "PAYPAL": "PYPL", "JPMORGAN": "JPM", "GOLDMAN": "GS",
            # German companies
            "SIEMENS": "SIE.DE", "BAYER": "BAYN.DE", "MERCEDES": "MBG.DE",
            "VOLKSWAGEN": "VOW3.DE", "VW": "VOW3.DE", "ADIDAS": "ADS.DE",
            "DEUTSCHE BANK": "DBK.DE", "ALLIANZ": "ALV.DE", "BASF": "BAS.DE",
            "DEUTSCHE TELEKOM": "DTE.DE", "TELEKOM": "DTE.DE",
        }
        
        # Keep backward compatibility aliases
        self._known_symbols = self._known_crypto_symbols
        self._name_to_symbol = self._crypto_name_to_symbol
    
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
    
    def _extract_symbols(self, text: str) -> Tuple[List[str], AssetType]:
        """
        Extract symbols from text and detect asset type.
        
        Returns:
            Tuple of (list of symbols, detected asset type)
        """
        text_upper = text.upper()
        crypto_found = []
        stock_found = []
        
        # Check for known crypto symbols
        for sym in self._known_crypto_symbols:
            if re.search(rf'\b{sym}\b', text_upper):
                crypto_found.append(f"{sym}USDT")
        
        # Check for crypto full names
        for name, sym in self._crypto_name_to_symbol.items():
            if re.search(rf'\b{name}\b', text_upper):
                symbol = f"{sym}USDT"
                if symbol not in crypto_found:
                    crypto_found.append(symbol)
        
        # Check for known stock symbols
        for sym in self._known_stock_symbols:
            if re.search(rf'\b{sym}\b', text_upper):
                if sym not in stock_found:
                    stock_found.append(sym)
        
        # Check for stock full names
        for name, sym in self._stock_name_to_symbol.items():
            if re.search(rf'\b{name}\b', text_upper):
                if sym not in stock_found:
                    stock_found.append(sym)
        
        # Check for stock patterns with exchange suffix (.DE, .L, etc.)
        stock_patterns = re.findall(r'\b([A-Z]{2,5})\.(DE|L|PA|MI|SW|AS)\b', text_upper)
        for match in stock_patterns:
            symbol = f"{match[0]}.{match[1]}"
            if symbol not in stock_found:
                stock_found.append(symbol)
        
        # Check for index symbols (^GSPC, ^DJI, etc.)
        index_patterns = re.findall(r'\^[A-Z]{2,6}', text_upper)
        for idx in index_patterns:
            if idx not in stock_found:
                stock_found.append(idx)
        
        # Detect keywords that indicate asset type
        stock_keywords = ["stock", "aktie", "share", "etf", "index", "dax", "s&p", "dow", "nasdaq"]
        crypto_keywords = ["crypto", "krypto", "coin", "token", "defi", "nft"]
        
        has_stock_keyword = any(kw in text.lower() for kw in stock_keywords)
        has_crypto_keyword = any(kw in text.lower() for kw in crypto_keywords)
        
        # Determine asset type
        if stock_found and not crypto_found:
            asset_type = AssetType.STOCK
            return (stock_found, asset_type)
        elif crypto_found and not stock_found:
            asset_type = AssetType.CRYPTO
            return (crypto_found, asset_type)
        elif stock_found and crypto_found:
            # Mixed - use keywords to decide, default to crypto
            if has_stock_keyword and not has_crypto_keyword:
                return (stock_found, AssetType.STOCK)
            else:
                return (crypto_found, AssetType.CRYPTO)
        elif has_stock_keyword:
            return ([], AssetType.STOCK)
        elif has_crypto_keyword:
            return ([], AssetType.CRYPTO)
        else:
            return ([], AssetType.UNKNOWN)
    
    def _extract_symbols_legacy(self, text: str) -> List[str]:
        """
        Legacy method for backward compatibility.
        Extracts crypto symbols only.
        """
        symbols, _ = self._extract_symbols(text)
        return symbols
    
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
            
            # Detect asset type from LLM response or pattern matching
            asset_type_str = data.get("asset_type", "unknown").lower()
            if asset_type_str == "crypto":
                asset_type = AssetType.CRYPTO
            elif asset_type_str == "stock":
                asset_type = AssetType.STOCK
            else:
                # Fallback to pattern detection
                _, detected_asset_type = self._extract_symbols(message)
                asset_type = detected_asset_type
            
            # Process symbols based on asset type
            llm_symbols = data.get("symbols", [])
            symbols = []
            
            if asset_type == AssetType.STOCK:
                # Stock symbols - keep as-is or add exchange suffix
                for sym in llm_symbols:
                    sym_upper = sym.upper().strip()
                    # Check if it's a known stock or needs suffix
                    if sym_upper in self._known_stock_symbols:
                        symbols.append(sym_upper)
                    elif sym_upper in self._stock_name_to_symbol:
                        symbols.append(self._stock_name_to_symbol[sym_upper])
                    else:
                        symbols.append(sym_upper)
            else:
                # Crypto symbols - add USDT suffix
                for sym in llm_symbols:
                    sym_upper = sym.upper().replace("USDT", "").strip()
                    if sym_upper in self._known_crypto_symbols:
                        symbols.append(f"{sym_upper}USDT")
                    elif sym_upper in self._crypto_name_to_symbol:
                        symbols.append(f"{self._crypto_name_to_symbol[sym_upper]}USDT")
                    else:
                        symbols.append(f"{sym_upper}USDT")
            
            # Also extract from original message in case LLM missed some
            msg_symbols, msg_asset_type = self._extract_symbols(message)
            for s in msg_symbols:
                if s not in symbols:
                    symbols.append(s)
            
            # Use message asset type if LLM didn't detect one
            if asset_type == AssetType.UNKNOWN and msg_asset_type != AssetType.UNKNOWN:
                asset_type = msg_asset_type
            
            confidence = float(data.get("confidence", 0.85))
            reason = data.get("reason", "LLM classification")
            
            # Determine tool hint for simple lookups (primary or sub-intent)
            tool_hint = None
            if intent_type == IntentType.SIMPLE_LOOKUP or IntentType.SIMPLE_LOOKUP in sub_intents:
                if asset_type == AssetType.STOCK:
                    tool_hint = "get_stock_price"
                else:
                    tool_hint = "get_realtime_price"
            
            # Log classification with asset type
            asset_info = f", asset_type={asset_type.value}" if asset_type != AssetType.UNKNOWN else ""
            if sub_intents:
                sub_names = [s.value for s in sub_intents]
                logger.info(f"LLM classified '{message[:50]}...' as {intent_type.value} with sub-intents {sub_names}{asset_info}")
            else:
                logger.info(f"LLM classified '{message[:50]}...' as {intent_type.value} (conf: {confidence:.2f}){asset_info}")
            
            return Intent(
                type=intent_type,
                confidence=confidence,
                entities={"symbols": symbols},
                tool_hint=tool_hint,
                reason=f"LLM: {reason}",
                sub_intents=sub_intents,
                asset_type=asset_type,
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
        symbols, asset_type = self._extract_symbols(message)
        entities = {"symbols": symbols}
        sub_intents = []
        
        # Empty message
        if not message_lower:
            return Intent(
                type=IntentType.CONVERSATION,
                confidence=1.0,
                entities=entities,
                reason="Empty message",
                asset_type=asset_type,
            )
        
        # Detect compound queries - check for multiple intent signals
        has_price_component = any(t in message_lower for t in ["price", "how much", "cost", "preis", "kurs"])
        has_chart_component = any(t in message_lower for t in ["chart", "graph", "dashboard", "visuali"])
        has_analysis_component = any(t in message_lower for t in [
            "analyze", "analysis", "situation", "outlook", "trend", 
            "recommend", "should i", "what do you think",
            "analysiere", "analyse", "empfehlung"
        ])
        has_report_component = any(t in message_lower for t in ["report", "document", "write up", "bericht"])
        has_comparison_component = any(t in message_lower for t in [" vs ", " versus ", "compare", "vergleich"])
        
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
            if asset_type == AssetType.STOCK and IntentType.SIMPLE_LOOKUP in sub_intents:
                tool_hint = "get_stock_price"
            
            return Intent(
                type=primary_type,
                confidence=0.8,
                entities=entities,
                tool_hint=tool_hint,
                reason=f"Compound query: {primary_type.value} with {[s.value for s in sub_intents]}",
                sub_intents=sub_intents,
                asset_type=asset_type,
            )
        
        # Simple price patterns (high confidence) - only if JUST price
        simple_patterns = [
            r"^what(?:'s| is) the (?:current )?price",
            r"^(?:get|show|check) (?:the )?price",
            r"^how much (?:is|does)",
            r"^price of\b",
            r"^\w+ price\??$",
            r"^(?:current )?price",
            r"^(?:was|wie) (?:kostet|ist der (?:preis|kurs))",  # German
        ]
        
        for pattern in simple_patterns:
            if re.search(pattern, message_lower):
                # Make sure it's not also asking for analysis/chart/etc
                if not any(t in message_lower for t in ["analyze", "analysis", "trend", "signal", "recommend", "chart", "graph"]):
                    tool_hint = "get_stock_price" if asset_type == AssetType.STOCK else "get_realtime_price"
                    return Intent(
                        type=IntentType.SIMPLE_LOOKUP,
                        confidence=0.85,
                        entities=entities,
                        tool_hint=tool_hint,
                        reason="Matches simple price pattern",
                        asset_type=asset_type,
                    )
        
        # Analysis triggers
        analysis_triggers = [
            "analyze", "analysis", "analyse", "situation", "outlook",
            "forecast", "trend", "momentum", "signal", "recommend",
            "should i buy", "should i sell", "entry", "exit",
            "support", "resistance", "technical", "what do you think",
            "analysiere", "empfehlung", "prognose",  # German
        ]
        if any(t in message_lower for t in analysis_triggers):
            return Intent(
                type=IntentType.ANALYSIS,
                confidence=0.85,
                entities=entities,
                reason="Contains analysis triggers",
                asset_type=asset_type,
            )
        
        # Comparison triggers (check before chart triggers)
        comparison_triggers = [
            " vs ", " versus ", "compare", "comparison", 
            "better than", "which is better", "difference between",
            "vergleich", "vergleiche",  # German
        ]
        if any(t in message_lower for t in comparison_triggers):
            return Intent(
                type=IntentType.COMPARISON,
                confidence=0.85,
                entities=entities,
                reason="Contains comparison triggers",
                asset_type=asset_type,
            )
        
        # Chart triggers
        if any(t in message_lower for t in ["chart", "graph", "dashboard", "visuali"]):
            return Intent(
                type=IntentType.CHART,
                confidence=0.85,
                entities=entities,
                reason="Contains chart triggers",
                asset_type=asset_type,
            )
        
        # Report triggers
        if any(t in message_lower for t in ["report", "document", "write up", "bericht"]):
            return Intent(
                type=IntentType.REPORT,
                confidence=0.85,
                entities=entities,
                reason="Contains report triggers",
                asset_type=asset_type,
            )
        
        # Short message with symbols -> likely simple lookup
        if symbols and len(message.split()) <= 6:
            tool_hint = "get_stock_price" if asset_type == AssetType.STOCK else "get_realtime_price"
            asset_desc = "stock" if asset_type == AssetType.STOCK else "crypto"
            return Intent(
                type=IntentType.SIMPLE_LOOKUP,
                confidence=0.7,
                entities=entities,
                tool_hint=tool_hint,
                reason=f"Short message with {asset_desc} symbols",
                asset_type=asset_type,
            )
        
        # Default to analysis for anything with symbols
        if symbols:
            asset_desc = "stock" if asset_type == AssetType.STOCK else "crypto"
            return Intent(
                type=IntentType.ANALYSIS,
                confidence=0.6,
                entities=entities,
                reason=f"Contains {asset_desc} symbols, defaulting to analysis",
                asset_type=asset_type,
            )
        
        # Default fallback
        return Intent(
            type=IntentType.CONVERSATION,
            confidence=0.5,
            entities=entities,
            reason="No specific pattern matched",
            asset_type=asset_type,
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
    
    # =========================================================================
    # Strategy Classification (for Learning System)
    # =========================================================================
    
    def classify_strategy(self, message: str) -> Tuple[StrategyType, float]:
        """
        Classify the trading strategy type from user message.
        
        Uses pattern-based classification for fast, reliable results.
        Strategy classification is used to:
        - Isolate feedback loops (Range feedback doesn't affect Breakout metrics)
        - Inject relevant performance context into agent prompts
        - Track strategy-specific accuracy over time
        
        Args:
            message: User's query or analysis request
            
        Returns:
            Tuple of (StrategyType, confidence_score)
            
        Examples:
            >>> router.classify_strategy("Analyze BTC for breakout setup")
            (StrategyType.BREAKOUT_PULLBACK, 0.85)
            
            >>> router.classify_strategy("Is ETH in a good range for swing trading?")
            (StrategyType.RANGE, 0.75)
        """
        message_lower = message.lower()
        
        # Score each strategy type by keyword matches
        scores: Dict[StrategyType, float] = {}
        
        for strategy_type, keywords in STRATEGY_KEYWORDS.items():
            score = 0.0
            matches = []
            for keyword in keywords:
                if keyword in message_lower:
                    # Longer keywords get higher weight
                    weight = min(len(keyword) / 10, 1.0) * 0.25
                    score += 0.25 + weight
                    matches.append(keyword)
            
            if score > 0:
                scores[strategy_type] = min(score, 1.0)
                logger.debug(f"Strategy {strategy_type.value}: {score:.2f} (matches: {matches})")
        
        if not scores:
            return (StrategyType.UNKNOWN, 0.0)
        
        # Return highest scoring strategy
        best_strategy = max(scores, key=scores.get)
        confidence = scores[best_strategy]
        
        logger.info(f"Strategy classified: {best_strategy.value} (conf: {confidence:.2f})")
        return (best_strategy, confidence)
    
    async def classify_strategy_async(self, message: str) -> Tuple[StrategyType, float]:
        """
        Classify strategy using LLM for better accuracy.
        
        Falls back to pattern-based classification if LLM unavailable.
        
        Args:
            message: User's query
            
        Returns:
            Tuple of (StrategyType, confidence_score)
        """
        client = self._get_model_client()
        if client is None:
            return self.classify_strategy(message)
        
        try:
            from autogen_core.models import UserMessage
            
            prompt = '''You are a trading strategy classifier. Classify the user's message into ONE strategy type.

Strategy types:
- **range**: Range/channel trading, sideways markets, bouncing between support/resistance
- **breakout_pullback**: Breakout trades, waiting for pullback/retest after breakout
- **trend_following**: Trading with the trend, momentum, moving average strategies
- **reversal**: Counter-trend trades, divergences, oversold/overbought reversals
- **scalping**: Very short-term trades, 1-15 minute timeframes, quick profits
- **unknown**: Cannot determine strategy from message

Respond ONLY with JSON: {"strategy": "<type>", "confidence": 0.0-1.0, "reason": "brief explanation"}

User message: ''' + message
            
            response = await client.create(
                messages=[UserMessage(content=prompt, source="user")],
                json_output=True,
            )
            
            content = response.content
            if isinstance(content, str):
                json_match = re.search(r'\{[^{}]*\}', content)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    data = json.loads(content)
            else:
                data = content
            
            strategy_str = data.get("strategy", "unknown").lower()
            strategy_type = STRATEGY_TYPE_MAP.get(strategy_str, StrategyType.UNKNOWN)
            confidence = float(data.get("confidence", 0.7))
            
            logger.info(f"LLM strategy classification: {strategy_type.value} (conf: {confidence:.2f})")
            return (strategy_type, confidence)
            
        except Exception as e:
            logger.warning(f"LLM strategy classification failed: {e}, using pattern fallback")
            return self.classify_strategy(message)


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
    """Format a single price result with source attribution."""
    try:
        if isinstance(data, str):
            parsed = json.loads(data)
        else:
            parsed = data
            
        if isinstance(parsed, dict):
            price = parsed.get("price") or parsed.get("current_price")
            change_24h = parsed.get("change_24h") or parsed.get("price_change_24h")
            
            # Extract source information
            source_info = parsed.get("_source", {})
            provider = source_info.get("provider") or parsed.get("provider", "")
            timestamp = source_info.get("timestamp", "")
            
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
                
                # Add source attribution
                if provider:
                    # Format timestamp if available
                    if timestamp:
                        # Extract just time portion if full ISO format
                        if "T" in str(timestamp):
                            time_part = str(timestamp).split("T")[1][:8]
                            output += f"\n📚 _Quelle: {provider} ({time_part} UTC)_"
                        else:
                            output += f"\n📚 _Quelle: {provider}_"
                    else:
                        output += f"\n📚 _Quelle: {provider}_"
                
                return output
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    
    # Fallback to raw result
    return f"💰 **{symbol}**: {data}" if symbol else str(data)
