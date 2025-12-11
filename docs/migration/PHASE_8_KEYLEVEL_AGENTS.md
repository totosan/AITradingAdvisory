# Phase 8: KeyLevel Analyzer + Spezialisierte Agent-Teams

**Status:** 📋 GEPLANT  
**Beginn:** TBD  
**Abhängigkeiten:** Phase 7 (Learning System) ✅

---

## Ziel

Implementierung eines **proaktiven Analyse-Systems** mit:
1. **KeyLevelAnalyzer** - Automatische S/R-Zonen-Erkennung (basierend auf Bjorgum Key Levels PineScript)
2. **CandlePatternScanner** - Candlestick-Patterns nur an relevanten Key Levels
3. **MarketPhaseDetector** - Automatische Erkennung von Marktphasen
4. **Spezialisierte Agent-Teams** - Strategy-spezifische Agent-Gruppen mit isoliertem Feedback

---

## Architektur-Übersicht

\`\`\`
┌─────────────────────────────────────────────────────────────────────────────┐
│                        🎯 MASTER ORCHESTRATOR                               │
│     "StrategyCoordinator" - Erkennt Marktphasen, delegiert an Teams         │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
       ┌────────────────────────┼────────────────────────┐
       ▼                        ▼                        ▼
┌──────────────┐      ┌──────────────────┐      ┌──────────────┐
│ 📊 Quick     │      │ 🧠 Strategy      │      │ 📝 Output    │
│ Data Team    │      │ Specialist Teams │      │ Team         │
│              │      │                  │      │              │
│ • PriceFetcher│     │ ┌─ RangeTeam     │      │ • ReportWriter│
│ • KeyLevelAn. │     │ ├─ BreakoutTeam  │      │ • ChartExporter│
│              │      │ ├─ TrendTeam     │      │ • AlertManager│
└──────────────┘      │ ├─ ReversalTeam  │      └──────────────┘
                      │ └─ ScalpingTeam  │
                      └────────┬─────────┘
                               │
         ┌─────────────────────┴─────────────────────┐
         ▼                                           ▼
 ┌─────────────────┐                        ┌─────────────────┐
 │ 📈 Range Team   │                        │ 🚀 Breakout Team│
 │                 │                        │                 │
 │ • RangeExpert   │  ← Eigene Feedback-   │ • BreakoutExpert│
 │ • S/R Analyst   │     Loop pro Team!    │ • FalseBreakDet.│
 │ • PatternScanner│                        │ • VolumeAnalyst │
 └─────────────────┘                        └─────────────────┘
\`\`\`

---

## Implementierungsschritte

### Step 1: KeyLevelAnalyzer Tool

**Datei:** \`src/keylevel_analyzer.py\`

**Funktionen (aus Bjorgum PineScript portiert):**

\`\`\`python
class KeyLevelAnalyzer:
    """
    Erkennt Support/Resistance Zonen aus OHLCV-Daten.
    Portiert von Bjorgum Key Levels PineScript.
    """
    
    def __init__(
        self,
        left: int = 20,           # Look-left für Pivot-Erkennung
        right: int = 15,          # Look-right für Pivot-Erkennung
        num_pivots: int = 4,      # Anzahl zu trackender Pivots
        atr_length: int = 30,     # ATR-Länge für Zone-Breite
        zone_atr_mult: float = 0.5,  # Zone-Breite als ATR-Multiplikator
        max_zone_percent: float = 5.0,  # Max Zone-Größe in %
        use_heiken_ashi: bool = True,   # HA-Bodies für glattere Levels
    ):
        ...
    
    def detect_pivots(self, df: pd.DataFrame) -> Dict[str, List[Dict]]:
        """Findet Swing Highs/Lows mit Look-Left/Right."""
        
    def create_zones(self, pivots: List[Dict], df: pd.DataFrame) -> List[Zone]:
        """Erstellt Zonen mit ATR-normalisierter Breite."""
        
    def merge_overlapping_zones(self, zones: List[Zone]) -> List[Zone]:
        """Verschmilzt überlappende Zonen → stärkere Konfidenz."""
        
    def detect_sr_flip(self, current_price: float, zones: List[Zone]) -> List[Dict]:
        """Erkennt Support→Resistance und Resistance→Support Flips."""
        
    def detect_false_break(self, df: pd.DataFrame, zones: List[Zone], lookback: int = 2) -> List[Dict]:
        """Erkennt Bull/Bear Traps (False Breaks)."""
        
    def detect_breakout(self, df: pd.DataFrame, zones: List[Zone]) -> Dict:
        """Erkennt echte Breakouts (Preis über/unter ALLEN Pivots)."""
        
    def analyze(self, df: pd.DataFrame) -> KeyLevelAnalysis:
        """Vollständige Analyse - kombiniert alle Methoden."""
\`\`\`

---

### Step 2: CandlePatternScanner Tool

**Datei:** \`src/candle_patterns.py\`

**Pattern-Typen (aus Bjorgum):**

| Bullish | Bearish | Neutral |
|---------|---------|---------|
| Hammer | Shooting Star | Doji |
| Bullish Engulfing | Bearish Engulfing | Spinning Top |
| Dragonfly Doji | Gravestone Doji | |
| Tweezer Bottom | Tweezer Top | |
| Piercing | Dark Cloud Cover | |
| Bullish Harami | Bearish Harami | |
| Long Lower Shadow | Long Upper Shadow | |

**Implementierung:**

\`\`\`python
class CandlePatternScanner:
    """Erkennt Candlestick-Patterns, gefiltert auf Key Levels."""
    
    def scan_all_patterns(
        self, 
        df: pd.DataFrame, 
        zones: List[Zone] = None,
        only_at_levels: bool = True,
    ) -> List[PatternMatch]:
        """Scannt nach allen aktivierten Patterns."""
\`\`\`

---

### Step 3: MarketPhaseDetector Agent

**Datei:** \`backend/app/agents/market_phase_detector.py\`

**Marktphasen:**
\`\`\`python
class MarketPhase(Enum):
    RANGING = "ranging"                    # Seitwärtsbewegung in Range
    TRENDING_UP = "trending_up"            # Klarer Aufwärtstrend
    TRENDING_DOWN = "trending_down"        # Klarer Abwärtstrend
    BREAKOUT_PENDING = "breakout_pending"  # Kurz vor Ausbruch
    VOLATILE = "volatile"                  # Hohe Volatilität
    REVERSAL_POSSIBLE = "reversal_possible"  # Trendumkehr-Signale
\`\`\`

**Erkennungslogik:**
- ADX < 25 → RANGING
- ADX > 25 + EMA-Ausrichtung → TRENDING
- Enge Bollinger + Preis nahe Zone → BREAKOUT_PENDING
- RSI-Divergenz + Preis an Zone → REVERSAL_POSSIBLE

---

### Step 4: Spezialisierte Agent-Teams

**Verzeichnis:** \`backend/app/agents/teams/\`

#### 4.1 RangeTeam (\`range_team.py\`)

\`\`\`python
class RangeTeam:
    """Spezialisiert auf Range-Trading."""
    agents = [RangeExpert, SupportResistanceAnalyst, PatternScanner]
    tools = ["analyze_key_levels", "scan_candle_patterns"]
    feedback_strategy = StrategyType.RANGE
\`\`\`

#### 4.2 BreakoutTeam (\`breakout_team.py\`)

\`\`\`python
class BreakoutTeam:
    """Spezialisiert auf Breakout-Trading."""
    agents = [BreakoutExpert, VolumeConfirmationAgent, FalseBreakDetector]
    tools = ["analyze_key_levels", "detect_false_break", "get_orderbook_depth"]
    feedback_strategy = StrategyType.BREAKOUT_PULLBACK
\`\`\`

#### 4.3 ReversalTeam (\`reversal_team.py\`)

\`\`\`python
class ReversalTeam:
    """Spezialisiert auf Trendumkehr-Trading."""
    agents = [DivergenceScanner, ExhaustionDetector, PatternAgent]
    feedback_strategy = StrategyType.REVERSAL
\`\`\`

#### 4.4 TrendTeam (\`trend_team.py\`)

\`\`\`python
class TrendTeam:
    """Spezialisiert auf Trend-Following."""
    agents = [TrendIdentifier, PullbackScanner, MomentumAnalyst]
    feedback_strategy = StrategyType.TREND_FOLLOWING
\`\`\`

---

### Step 5: StrategyCoordinator Erweiterung

**Datei:** \`backend/app/services/agent_service.py\`

**Änderungen:**

\`\`\`python
class AgentService:
    def __init__(self, user_id: Optional[str] = None):
        # ... existing code ...
        
        # Neue Komponenten
        self._keylevel_analyzer = KeyLevelAnalyzer()
        self._pattern_scanner = CandlePatternScanner()
        self._phase_detector = MarketPhaseDetector()
        
        # Team-Registry
        self._teams = {
            MarketPhase.RANGING: RangeTeam,
            MarketPhase.BREAKOUT_PENDING: BreakoutTeam,
            MarketPhase.REVERSAL_POSSIBLE: ReversalTeam,
            MarketPhase.TRENDING_UP: TrendTeam,
            MarketPhase.TRENDING_DOWN: TrendTeam,
            MarketPhase.VOLATILE: None,  # Fallback to full team
        }
    
    async def _detect_market_phase(self, symbol: str) -> MarketPhaseResult:
        """Erkennt Marktphase für Symbol."""
    
    async def _create_team_for_phase(self, phase: MarketPhase) -> MagenticOneGroupChat:
        """Erstellt das passende Team für die erkannte Marktphase."""
\`\`\`

---

### Step 6: Tool-Registrierung

**Datei:** \`src/tool_registry.py\`

**Neue Tools:**

\`\`\`python
def analyze_key_levels(symbol: str, interval: str = "1H") -> str:
    """Analysiert Key Levels (Support/Resistance) für ein Symbol."""
    
def scan_candle_patterns(symbol: str, interval: str = "1H", only_at_levels: bool = True) -> str:
    """Scannt nach Candlestick-Patterns."""
    
def detect_market_phase(symbol: str) -> str:
    """Erkennt die aktuelle Marktphase automatisch."""
\`\`\`

---

## Datei-Struktur nach Implementierung

\`\`\`
src/
├── keylevel_analyzer.py      # NEU: KeyLevel-Erkennung
├── candle_patterns.py        # NEU: Pattern-Scanner
├── crypto_tools.py           # Bestehend
├── exchange_tools.py         # Bestehend
└── tool_registry.py          # Erweitert

backend/app/
├── agents/                    # NEU: Agent-Definitionen
│   ├── __init__.py
│   ├── market_phase_detector.py
│   └── teams/
│       ├── __init__.py
│       ├── range_team.py
│       ├── breakout_team.py
│       ├── reversal_team.py
│       └── trend_team.py
├── services/
│   └── agent_service.py      # Erweitert: Team-Routing

tests/
├── test_keylevel_analyzer.py # NEU
├── test_candle_patterns.py   # NEU
└── test_market_phase.py      # NEU
\`\`\`

---

## Implementierungsreihenfolge

| # | Task | Aufwand | Abhängigkeiten |
|---|------|---------|----------------|
| 1 | \`keylevel_analyzer.py\` | 4h | - |
| 2 | \`candle_patterns.py\` | 3h | - |
| 3 | Tests für Step 1+2 | 2h | 1, 2 |
| 4 | \`market_phase_detector.py\` | 2h | 1 |
| 5 | Agent-Teams (Range, Breakout) | 3h | 4 |
| 6 | Agent-Teams (Reversal, Trend) | 2h | 4 |
| 7 | \`agent_service.py\` Erweiterung | 3h | 4, 5, 6 |
| 8 | Tool-Registrierung | 1h | 1, 2 |
| 9 | Integration Tests | 2h | 7, 8 |
| 10 | Dokumentation | 1h | 9 |

**Gesamt: ~23h**

---

## Erwartete Ergebnisse

### Vorher (Phase 7)
\`\`\`
User: "Analysiere BTC"
→ 6 Agents arbeiten parallel
→ Generische Analyse
\`\`\`

### Nachher (Phase 8)
\`\`\`
User: "Analysiere BTC"
→ MarketPhaseDetector: "BTC ist in RANGE (94k-98k), Konfidenz 82%"
→ RangeTeam wird aktiviert (3 spezialisierte Agents)
→ Strukturierte Empfehlung:
  {
    "phase": "RANGE",
    "action": "BUY",
    "entry": 94200,
    "stop_loss": 93500,
    "take_profit": [96000, 97800],
    "confidence": 0.78
  }
\`\`\`

---

## Referenzen

- Bjorgum Key Levels PineScript: \`docs/pinescripts/bj keylevels.pine\`
- Phase 7 Learning System: \`docs/migration/PHASE_7_LEARNING_SYSTEM.md\`
- AutoGen MagenticOne: [Microsoft AutoGen Docs](https://microsoft.github.io/autogen/)
