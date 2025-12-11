"""
Range Team for AITradingAdvisory.

Specialized agent team for range-bound/consolidation markets.
Focuses on support/resistance trading, mean reversion, and
pattern detection at key levels.

Agents:
- RangeExpert: Strategic analysis for range trading
- SupportResistanceAnalyst: Key level identification
- PatternScanner: Candlestick pattern detection at levels

Tools:
- analyze_key_levels: Detect S/R zones
- scan_candle_patterns: Detect patterns at levels
- get_realtime_price: Current price data
- get_ohlcv_data: Historical OHLCV data
"""

import sys
from pathlib import Path
from typing import List, Optional, Callable, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from intent_router import StrategyType
from .base_team import BaseTeam, TeamConfig


# Team configuration
RANGE_TEAM_CONFIG = TeamConfig(
    name="RangeTeam",
    description="Specialized team for range-bound market trading",
    feedback_strategy=StrategyType.RANGE,
    agents=[
        "RangeExpert",
        "SupportResistanceAnalyst",
        "PatternScanner",
    ],
    tools=[
        "analyze_key_levels",
        "scan_candle_patterns",
        "get_realtime_price",
        "get_ohlcv_data",
        "detect_false_break",
    ],
    focus_area="Range trading, S/R bounces, mean reversion",
    max_turns=8,
    system_prompt_additions="""
🎯 RANGE TRADING SPEZIALIST

Du bist Teil des Range-Trading Teams, spezialisiert auf:
- Support/Resistance Zone Trading
- Mean Reversion Strategien
- Range-Bound Marktbedingungen

STRATEGIE-REGELN:
1. BUY nur an Support-Zonen (untere Range-Grenze)
2. SELL nur an Resistance-Zonen (obere Range-Grenze)
3. KEINE Trades mitten in der Range
4. Stop-Loss AUSSERHALB der Range setzen
5. Take-Profit an der gegenüberliegenden Zone

SIGNAL-QUALITÄT:
✅ Starkes Signal: Pattern (Hammer/Engulfing) + S/R Zone + RSI-Bestätigung
⚠️ Mittleres Signal: Nur S/R Zone + Pattern
❌ Schwaches Signal: Nur Preis an Zone ohne Bestätigung

RISIKO-MANAGEMENT:
- Position Size: 1-2% des Kapitals
- R:R Minimum: 1.5:1 (Range-Breite erlaubt gutes R:R)
- Max Verlust pro Trade: 1% des Kapitals
""",
)


class RangeTeam(BaseTeam):
    """
    Range Trading Team - optimized for consolidation markets.
    
    This team excels at:
    - Identifying support and resistance zones
    - Detecting high-probability reversal patterns at key levels
    - Mean reversion entry and exit timing
    - False breakout detection (bull/bear traps)
    """
    
    config = RANGE_TEAM_CONFIG
    
    def __init__(self, model_client=None, user_id: Optional[str] = None):
        super().__init__(model_client, user_id)
        self._load_tools()
    
    def _load_tools(self) -> None:
        """Load the tool functions for this team."""
        try:
            from keylevel_analyzer import analyze_key_levels, detect_false_break
            from candle_patterns import scan_candle_patterns
            from exchange_tools import get_realtime_price, get_ohlcv_data
            
            self._tools = [
                analyze_key_levels,
                detect_false_break,
                scan_candle_patterns,
                get_realtime_price,
                get_ohlcv_data,
            ]
        except ImportError as e:
            import logging
            logging.warning(f"Could not load all Range Team tools: {e}")
            self._tools = []
    
    def get_tools(self) -> List[Callable]:
        """Get tool functions for Range Team agents."""
        return self._tools
    
    def get_agent_prompts(self) -> dict:
        """
        Get specialized prompts for each agent in the Range Team.
        
        Returns:
            Dict mapping agent name to system prompt
        """
        base_addition = self.config.system_prompt_additions
        feedback = self.get_feedback_context()
        
        prompts = {
            "RangeExpert": f"""
Du bist der Range-Trading Experte und Koordinator des Teams.

DEINE AUFGABEN:
1. Marktphase bestätigen (ist es wirklich eine Range?)
2. Range-Grenzen definieren (High/Low der Range)
3. Entry-Strategie festlegen (Support Buy / Resistance Sell)
4. Risiko/Reward berechnen
5. Final Trade-Empfehlung geben

ANALYSE-WORKFLOW:
1. Rufe analyze_key_levels() auf um S/R Zonen zu identifizieren
2. Prüfe ob Preis nahe einer Zone ist
3. Wenn ja, lasse PatternScanner nach Bestätigungs-Patterns suchen
4. Berechne Entry, Stop-Loss, Take-Profit

{base_addition}

{f'📊 HISTORISCHES FEEDBACK:{chr(10)}{feedback}' if feedback else ''}
""",
            "SupportResistanceAnalyst": f"""
Du bist der Support/Resistance Analyst.

DEINE AUFGABEN:
1. Key Levels mit analyze_key_levels() identifizieren
2. Zonen-Stärke bewerten (wie oft getestet?)
3. S/R Flips erkennen (Support wird Resistance und umgekehrt)
4. False Breaks mit detect_false_break() erkennen

OUTPUT FORMAT:
- Liste aller relevanten Zonen mit Stärke
- Aktuelle Position des Preises relativ zu Zonen
- Warnung bei False Break Signalen

{base_addition}
""",
            "PatternScanner": f"""
Du bist der Candlestick Pattern Scanner.

DEINE AUFGABEN:
1. Patterns mit scan_candle_patterns(only_at_levels=True) erkennen
2. Pattern-Qualität bewerten
3. Nur Patterns an Key Levels als relevant einstufen

WICHTIGE PATTERNS FÜR RANGE-TRADING:
- Hammer/Shooting Star an S/R
- Bullish/Bearish Engulfing an S/R
- Doji an S/R (Unentschlossenheit)
- Tweezer Top/Bottom

{base_addition}
""",
        }
        
        return prompts


def create_range_team(
    model_client: Any,
    user_id: Optional[str] = None,
) -> RangeTeam:
    """
    Factory function to create a configured Range Team.
    
    Args:
        model_client: LLM client for agent creation
        user_id: Optional user ID for user-scoped feedback
        
    Returns:
        Configured RangeTeam instance
    """
    return RangeTeam(model_client=model_client, user_id=user_id)
