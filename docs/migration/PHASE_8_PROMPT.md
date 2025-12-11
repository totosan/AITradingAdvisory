# Phase 8 Implementierungs-Prompt

**Kopiere diesen Prompt in eine neue Chat-Session:**

---

## Context

Ich arbeite an einem AITradingAdvisory Projekt - einem Multi-Agent-System für Krypto-Analyse mit AutoGen MagenticOne. Das Projekt hat folgende abgeschlossene Phasen:

- Phase 1-5: Backend (FastAPI), Frontend (React), WebSocket, Secrets, Docker
- Phase 6: Multi-User System mit JWT Auth
- Phase 7: Learning System mit Strategy-isoliertem Feedback

## Aufgabe: Phase 8 implementieren

Bitte lies zuerst diese Dateien:
1. `docs/migration/PHASE_8_KEYLEVEL_AGENTS.md` - Der vollständige Implementierungsplan
2. `docs/pinescripts/bj keylevels.pine` - Das PineScript als Referenz für die Logik
3. `backend/app/services/agent_service.py` - Aktueller Agent-Service
4. `src/intent_router.py` - Bestehender IntentRouter mit StrategyType

## Implementiere in dieser Reihenfolge:

### Step 1: KeyLevelAnalyzer Tool
Erstelle `src/keylevel_analyzer.py` mit:
- Pivot-basierte S/R-Erkennung (ta.pivothigh/pivotlow Äquivalent)
- ATR-normalisierte Zonen (Zone = Pivot ± ATR*0.5)
- Zone Merging (überlappende Zonen verschmelzen)
- False Break Detection (Bull/Bear Traps)
- Heiken Ashi Berechnung für glattere Pivots

Orientiere dich an der Bjorgum PineScript Logik:
- `left=20, right=15` für Pivot-Lookback
- `zone_width = min(atr * 0.5, price * 0.05)` für Zone-Breite
- `_align()` Funktion für Zone-Merging
- `_falseBreak()` für Trap-Erkennung

### Step 2: CandlePatternScanner Tool
Erstelle `src/candle_patterns.py` mit:
- 16 Pattern-Typen (Hammer, Engulfing, Doji, etc.)
- ATR-basierte Größenfilter (keine Micro-Patterns)
- `only_at_levels=True` Option (Patterns nur an S/R)
- Filter aus PineScript: `hammerFib=33%`, `dojiSize=5%`, `hammerSize=0.1*ATR`

### Step 3: MarketPhaseDetector
Erstelle `backend/app/agents/market_phase_detector.py` mit:
- MarketPhase Enum (RANGING, TRENDING_UP, TRENDING_DOWN, BREAKOUT_PENDING, VOLATILE, REVERSAL_POSSIBLE)
- Phase-Erkennung via ADX (<25 = ranging), RSI, Bollinger Width, KeyLevels
- Confidence Score basierend auf Indikator-Übereinstimmung

### Step 4: Agent-Teams
Erstelle `backend/app/agents/teams/`:
- `range_team.py` - RangeExpert, SupportResistanceAnalyst, PatternScanner
- `breakout_team.py` - BreakoutExpert, VolumeConfirmationAgent, FalseBreakDetector
- Jedes Team mit eigenem `feedback_strategy` für isoliertes Feedback aus Phase 7

### Step 5: AgentService erweitern
In `backend/app/services/agent_service.py`:
- `_detect_market_phase(symbol)` hinzufügen
- Team-Routing basierend auf Marktphase
- Fallback zu vollem 6-Agent-Team bei VOLATILE oder unklarer Phase

### Step 6: Tests
Erstelle Tests für alle neuen Komponenten in `tests/`.

## Wichtige Constraints:

1. **Pandas für Berechnungen** - OHLCV-Daten kommen als DataFrame
2. **JSON-Output für Tools** - Alle Tools müssen `str` (JSON) zurückgeben
3. **Kompatibel mit Phase 7** - Nutze `StrategyType` Enum aus `src/intent_router.py`
4. **UV für Packages** - Nutze `uv pip install`, nicht `pip`
5. **Annotated für Tool-Parameter** - `from typing import Annotated`

## Beispiel-Output KeyLevelAnalyzer:

```json
{
  "zones": [
    {"top": 98200, "bottom": 97800, "type": "resistance", "strength": 3, "created_bar": 45},
    {"top": 94400, "bottom": 94000, "type": "support", "strength": 2, "created_bar": 32}
  ],
  "current_position": {
    "in_zone": true,
    "zone_type": "support",
    "distance_to_resistance": 0.04,
    "zones_above": 2,
    "zones_below": 1
  },
  "false_breaks": [
    {"type": "false_breakdown", "bar_index": 145, "zone_bottom": 94000}
  ],
  "breakout_status": {
    "is_breakout": false,
    "direction": null,
    "zones_broken": 0
  }
}
```

## Beispiel-Output MarketPhaseDetector:

```json
{
  "phase": "RANGING",
  "confidence": 0.82,
  "range": {"low": 94000, "high": 98000},
  "indicators": {
    "adx": 18.5,
    "rsi": 52,
    "bb_width": 0.03,
    "price_in_zone": true
  },
  "recommendation": "Range-Trading empfohlen: Buy at support, sell at resistance"
}
```

## PineScript Logik-Referenz:

Aus `docs/pinescripts/bj keylevels.pine`:

```
// Pivot Detection
pivot_high = ta.pivothigh(srcHigh, left, right)
pivot_low  = ta.pivotlow(srcLow, left, right)

// Zone Width (ATR-normalized)
band = math.min(atr * mult, perc) / 2
HH = pivot_high + band
HL = pivot_high - band

// False Break Detection
_falseBreak(_l) =>
    for i = 1 to lookback
        if _l[i] < _l and _l[i+1] >= _l and _l[1] < _l 
            _d := true  // False breakdown detected

// Zone Alignment (Merge overlapping)
if _T > _b and _T < _t or _B < _t and _B > _b
    // Zones overlap → merge them
```

Beginne mit Step 1 (KeyLevelAnalyzer) und zeige mir den Code.

---
