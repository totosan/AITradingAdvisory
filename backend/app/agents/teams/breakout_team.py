"""
Breakout Team for AITradingAdvisory.

Specialized agent team for breakout trading markets.
Focuses on breakout detection, volume confirmation, and
false breakout identification.

Agents:
- BreakoutExpert: Strategic analysis for breakout trading
- VolumeConfirmationAgent: Volume analysis for breakout validation
- FalseBreakDetector: Identifies failed breakouts (bull/bear traps)

Tools:
- analyze_key_levels: Detect S/R zones for breakout levels
- detect_false_break: Identify bull/bear traps
- get_orderbook_depth: Volume and liquidity analysis
- get_ohlcv_data: Historical OHLCV data with volume
"""

import sys
from pathlib import Path
from typing import List, Optional, Callable, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from intent_router import StrategyType
from .base_team import BaseTeam, TeamConfig


# Team configuration
BREAKOUT_TEAM_CONFIG = TeamConfig(
    name="BreakoutTeam",
    description="Specialized team for breakout trading",
    feedback_strategy=StrategyType.BREAKOUT_PULLBACK,
    agents=[
        "BreakoutExpert",
        "VolumeConfirmationAgent",
        "FalseBreakDetector",
    ],
    tools=[
        "analyze_key_levels",
        "detect_false_break",
        "get_orderbook_depth",
        "get_ohlcv_data",
        "get_realtime_price",
    ],
    focus_area="Breakout trading, volume confirmation, false break detection",
    max_turns=8,
    system_prompt_additions="""
🚀 BREAKOUT TRADING SPEZIALIST

Du bist Teil des Breakout-Trading Teams, spezialisiert auf:
- Breakout Erkennung und Bestätigung
- Volumen-Analyse für Breakout-Validierung
- False Breakout (Bull/Bear Trap) Erkennung
- Pullback-Entry nach Breakout

STRATEGIE-REGELN:
1. BREAKOUT: Preis schließt ÜBER Resistance oder UNTER Support
2. VOLUMEN: Breakout muss mit erhöhtem Volumen erfolgen (>1.5x Durchschnitt)
3. RETEST: Idealerweise Pullback zum gebrochenen Level abwarten
4. FALSE BREAK: Bei Rückkehr in die Range NICHT einsteigen!

ENTRY-TYPEN:
A) Aggressiv: Sofort beim Breakout-Close
B) Konservativ: Beim Pullback/Retest des gebrochenen Levels

SIGNAL-QUALITÄT:
✅ Starkes Breakout: Close über Level + Hohes Volumen + Kein False Break
⚠️ Riskantes Breakout: Nur Wick über Level oder geringes Volumen
❌ False Breakout: Preis kehrt in Range zurück = TRAP!

RISIKO-MANAGEMENT:
- Stop-Loss: Unter dem gebrochenen Level (für Long) oder darüber (für Short)
- Position Size: 1-2% des Kapitals (höher bei bestätigten Breakouts)
- R:R Minimum: 2:1 (Breakouts können große Moves erzeugen)
""",
)


class BreakoutTeam(BaseTeam):
    """
    Breakout Trading Team - optimized for breakout markets.
    
    This team excels at:
    - Identifying imminent breakout levels
    - Confirming breakouts with volume analysis
    - Detecting false breakouts (bull/bear traps)
    - Timing entries on breakout pullbacks
    """
    
    config = BREAKOUT_TEAM_CONFIG
    
    def __init__(self, model_client=None, user_id: Optional[str] = None):
        super().__init__(model_client, user_id)
        self._load_tools()
    
    def _load_tools(self) -> None:
        """Load the tool functions for this team."""
        try:
            from keylevel_analyzer import analyze_key_levels, detect_false_break
            from exchange_tools import get_realtime_price, get_ohlcv_data, get_orderbook_depth
            
            self._tools = [
                analyze_key_levels,
                detect_false_break,
                get_realtime_price,
                get_ohlcv_data,
                get_orderbook_depth,
            ]
        except ImportError as e:
            import logging
            logging.warning(f"Could not load all Breakout Team tools: {e}")
            self._tools = []
    
    def get_tools(self) -> List[Callable]:
        """Get tool functions for Breakout Team agents."""
        return self._tools
    
    def get_agent_prompts(self) -> dict:
        """
        Get specialized prompts for each agent in the Breakout Team.
        
        Returns:
            Dict mapping agent name to system prompt
        """
        base_addition = self.config.system_prompt_additions
        feedback = self.get_feedback_context()
        
        prompts = {
            "BreakoutExpert": f"""
Du bist der Breakout-Trading Experte und Koordinator des Teams.

DEINE AUFGABEN:
1. Breakout-Kandidaten identifizieren (enge Range + Preis an Level)
2. Breakout-Richtung einschätzen (bullish/bearish Bias)
3. Entry-Strategie festlegen (Aggressiv vs. Pullback-Entry)
4. Breakout vs. False Breakout unterscheiden
5. Final Trade-Empfehlung mit Entry/SL/TP geben

ANALYSE-WORKFLOW:
1. Rufe analyze_key_levels() auf - prüfe breakout_status
2. Wenn "breakout_pending": Bereite Setup vor
3. Bei aktivem Breakout: VolumeAgent nach Bestätigung fragen
4. FalseBreakDetector prüfen lassen

BREAKOUT-KRITERIEN:
✓ Preis SCHLIESSE über/unter dem Level (nicht nur Wick)
✓ Volumen mindestens 1.5x Durchschnitt
✓ Kein sofortiger Rücklauf in die Range
✓ Idealerweise: Vorherige Konsolidierung (enge BBs)

{base_addition}

{f'📊 HISTORISCHES FEEDBACK:{chr(10)}{feedback}' if feedback else ''}
""",
            "VolumeConfirmationAgent": f"""
Du bist der Volumen-Analyse Spezialist.

DEINE AUFGABEN:
1. Volumen beim Breakout analysieren (höher als Durchschnitt?)
2. Orderbook-Tiefe prüfen (gibt es Liquidität?)
3. Volume Profile analysieren (wo liegt das meiste Volumen?)
4. Breakout-Qualität basierend auf Volumen bewerten

VOLUMEN-REGELN:
- Gutes Breakout: Volumen > 1.5x des 20-Perioden-Durchschnitts
- Schwaches Breakout: Volumen normal oder niedrig = Vorsicht!
- Climactic Volumen: Extrem hohes Volumen kann Erschöpfung signalisieren

TOOLS:
- get_ohlcv_data() für Volumen-Historie
- get_orderbook_depth() für aktuelle Liquidität

OUTPUT:
- Volumen-Verhältnis (aktuell vs. Durchschnitt)
- Orderbook-Imbalance (mehr Bids oder Asks?)
- Volumen-Bestätigung: JA/NEIN mit Begründung

{base_addition}
""",
            "FalseBreakDetector": f"""
Du bist der False Breakout (Trap) Spezialist.

DEINE AUFGABEN:
1. False Breaks mit detect_false_break() erkennen
2. Bull/Bear Traps identifizieren
3. Warnung bei hohem Trap-Risiko geben
4. Trap-Trading Opportunities erkennen (Counter-Trade)

FALSE BREAK ERKENNUNG:
- Bull Trap: Preis bricht über Resistance, fällt dann zurück
- Bear Trap: Preis bricht unter Support, steigt dann zurück
- Typisch: Schnelle Rückkehr in die Range binnen 1-3 Kerzen

TRAP-RISIKO FAKTOREN:
⚠️ Niedriges Volumen beim Breakout
⚠️ Langer Wick über/unter dem Level
⚠️ Entgegengesetzte Divergenz (RSI macht nicht mit)
⚠️ Wichtiges News-Event bevor

OUTPUT:
- Trap-Risiko: HOCH/MITTEL/NIEDRIG
- Erkannte False Breaks (falls vorhanden)
- Empfehlung: Breakout vertrauen oder meiden?

{base_addition}
""",
        }
        
        return prompts


def create_breakout_team(
    model_client: Any,
    user_id: Optional[str] = None,
) -> BreakoutTeam:
    """
    Factory function to create a configured Breakout Team.
    
    Args:
        model_client: LLM client for agent creation
        user_id: Optional user ID for user-scoped feedback
        
    Returns:
        Configured BreakoutTeam instance
    """
    return BreakoutTeam(model_client=model_client, user_id=user_id)
