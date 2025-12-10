# Phase 7: Agent Learning & Feedback System

> **Status**: 🔄 In Progress  
> **Started**: 2025-12-09  
> **Goal**: Strategie-bewusstes Lern- und Feedback-System für kontinuierliche Verbesserung der Trading-Analysen

---

## Übersicht

Diese Phase implementiert ein geschlossenes Feedback-Loop-System, das:
- Trading-Predictions (Entry/SL/TP) pro Strategie-Typ speichert
- Predictions gegen tatsächliche Marktdaten evaluiert
- Performance-Metriken pro Strategie aggregiert
- Token-effizient Feedback-Kontext an Agenten zurückspielt
- Strategie-übergreifende "Global Insights" erfasst

### Design-Prinzipien

| Prinzip | Umsetzung |
|---------|-----------|
| **Strategie-Isolation** | Jede Prediction hat `strategy_type` – Feedback von Range-Trading beeinflusst nicht Breakout-Pullback |
| **Token-Effizienz** | Kompakte Summaries (~100-200 Tokens) statt voller History |
| **Query-Klassifizierung** | Erweiterung des bestehenden `IntentRouter` um Strategie-Erkennung |
| **Global Insights** | Strategie-übergreifende Erkenntnisse (z.B. "SL-Abstände generell zu eng") |
| **Spätere ML-Erweiterung** | Regelbasiertes Scoring jetzt, ML-basiertes Learning später |

### Architektur

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Query                                      │
│                    "Analysiere BTCUSDT für Breakout-Setup"                  │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         IntentRouter (erweitert)                            │
│                                                                              │
│  classify_intent() ────────► IntentType (price, analysis, chart, ...)       │
│  classify_strategy() ──────► StrategyType (breakout_pullback, range, ...)   │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       FeedbackContextService                                 │
│                                                                              │
│  get_strategy_context(user_id, strategy_type) → ~150 Tokens                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ "Deine Breakout-Performance (letzte 10):                            │   │
│  │  - Win Rate: 65%, Avg Score: 72                                     │   │
│  │  - Stärke: Timing bei Volumen-Confirmation                          │   │
│  │  - Schwäche: SL oft zu eng (3x ausgestoppt vor TP)                  │   │
│  │  Global: Entry-Präzision verbessern (+5% bei weiterem SL)"          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AgentService                                        │
│                                                                              │
│  TechnicalAnalyst System Prompt + Feedback Context                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ "Du bist ein Technical Analyst...                                   │   │
│  │  [DEIN PERFORMANCE FEEDBACK]                                        │   │
│  │  {feedback_context}                                                 │   │
│  │  Berücksichtige diese Learnings bei deiner Analyse."                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Agent Analysis                                       │
│                                                                              │
│  TechnicalAnalyst generiert strukturierte Prediction:                       │
│  {                                                                           │
│    "strategy_type": "breakout_pullback",                                    │
│    "symbol": "BTCUSDT",                                                     │
│    "direction": "long",                                                     │
│    "entry": 98500,                                                          │
│    "stop_loss": 97000,                                                      │
│    "take_profit": [100000, 102000],                                         │
│    "confidence": "high"                                                     │
│  }                                                                          │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PredictionService                                      │
│                                                                              │
│  extract_predictions_from_message() → Parse Agent Output                    │
│  save_prediction() ──────────────► SQLite: predictions table                │
│  evaluate_prediction() ──────────► Vergleich mit aktuellem Markt            │
│  calculate_scores() ─────────────► Accuracy, Timing, R:R Scores             │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SQLite Database                                     │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │   predictions    │  │ prediction_evals │  │  global_insights │          │
│  │                  │  │                  │  │                  │          │
│  │ id               │  │ id               │  │ id               │          │
│  │ user_id ────────►│  │ prediction_id───►│  │ user_id          │          │
│  │ strategy_type    │  │ evaluated_at     │  │ insight_type     │          │
│  │ symbol           │  │ price_at_eval    │  │ description      │          │
│  │ direction        │  │ mfe (max profit) │  │ source_strategy  │          │
│  │ entry_price      │  │ mae (max loss)   │  │ applies_to_all   │          │
│  │ stop_loss        │  │                  │  │ confidence       │          │
│  │ take_profit[]    │  └──────────────────┘  │ created_at       │          │
│  │ confidence       │                        └──────────────────┘          │
│  │ status           │                                                       │
│  │ outcome          │                                                       │
│  │ accuracy_score   │                                                       │
│  │ created_at       │                                                       │
│  └──────────────────┘                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Evaluation Scheduler                                    │
│                                                                              │
│  Background Task (alle 15 Min):                                             │
│  1. Liste aktive Predictions                                                │
│  2. Hole aktuelle Marktpreise via exchange_tools                            │
│  3. Prüfe: SL getroffen? TP getroffen? Expired?                            │
│  4. Update Status + berechne Scores                                         │
│  5. Generiere Global Insights bei Patterns                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Strategie-Typen

| Strategy Type | Keywords zur Erkennung | Beschreibung |
|---------------|------------------------|--------------|
| `range` | "range", "seitwärts", "channel", "consolidation" | Trading innerhalb definierter Grenzen |
| `breakout_pullback` | "breakout", "ausbruch", "pullback", "retest" | Entry nach Breakout + Pullback zum Level |
| `trend_following` | "trend", "momentum", "ema cross", "moving average" | Mit dem Trend handeln |
| `reversal` | "reversal", "umkehr", "divergence", "oversold", "overbought" | Gegen erschöpfte Trends |
| `scalping` | "scalp", "quick", "short-term", "5m", "15m" | Schnelle Trades auf kleinen Timeframes |

---

## Implementation Steps

### Step 1: Dokumentation ✅
- [x] PHASE_7_LEARNING_SYSTEM.md erstellen

### Step 2: Database Models 🔄
- [ ] `StrategyType` Enum in `backend/app/models/database.py`
- [ ] `Prediction` Model mit strategy_type, entry/SL/TP, outcome, scores
- [ ] `PredictionEvaluation` Model für Markt-Snapshots
- [ ] `GlobalInsight` Model für strategie-übergreifende Learnings
- [ ] Alembic Migration erstellen

### Step 3: IntentRouter Erweiterung
- [ ] `StrategyType` Enum in `src/intent_router.py`
- [ ] `classify_strategy()` Methode mit Keyword-Matching
- [ ] Unit Tests für Strategie-Klassifizierung

### Step 4: PredictionRepository
- [ ] CRUD Operations in `backend/app/core/repositories.py`
- [ ] `list_by_strategy()` Filter
- [ ] `get_performance_stats()` Aggregation
- [ ] `list_active_for_evaluation()` für Scheduler

### Step 5: PredictionService
- [ ] Neue Datei `backend/app/services/prediction_service.py`
- [ ] `extract_predictions_from_message()` – JSON-Parsing aus Agent-Output
- [ ] `save_prediction()` – Mit User + Conversation Link
- [ ] `evaluate_prediction()` – Vergleich mit Marktdaten
- [ ] `calculate_accuracy_score()` – Scoring-Logik

### Step 6: FeedbackContextService
- [ ] Neue Datei `backend/app/services/feedback_context.py`
- [ ] `get_strategy_context()` – Kompakte Performance-Summary
- [ ] `get_global_insights()` – Strategie-übergreifende Learnings
- [ ] Token-Budget-Management (~200 Token Cap)

### Step 7: AgentService Integration
- [ ] Strategy-Klassifizierung vor Prompt-Build
- [ ] Feedback-Kontext in TechnicalAnalyst System-Prompt injizieren
- [ ] Prediction-Extraktion nach Agent-Response

### Step 8: API Endpoints
- [ ] Neue Datei `backend/app/api/routes/predictions.py`
- [ ] `GET /api/v1/predictions` – Liste User-Predictions
- [ ] `GET /api/v1/predictions/{id}` – Prediction Details
- [ ] `POST /api/v1/predictions/{id}/feedback` – User Rating
- [ ] `GET /api/v1/predictions/stats` – Performance Dashboard

### Step 9: Evaluation Scheduler
- [ ] Background Task für periodische Evaluation
- [ ] Integration mit `exchange_tools.get_realtime_price()`
- [ ] Global Insight Generation bei erkannten Patterns

---

## API Endpoints

### Predictions

```
GET  /api/v1/predictions
     Query: ?strategy_type=breakout_pullback&status=active&limit=20
     → Liste der User-Predictions

GET  /api/v1/predictions/{id}
     → Prediction Details inkl. Evaluations

POST /api/v1/predictions/{id}/feedback
     Body: {"rating": "helpful", "comment": "SL war perfekt"}
     → User-Feedback speichern

GET  /api/v1/predictions/stats
     Query: ?strategy_type=breakout_pullback&days=30
     → Aggregierte Performance-Metriken
```

### Response Beispiele

**GET /api/v1/predictions/stats?strategy_type=breakout_pullback**
```json
{
  "strategy_type": "breakout_pullback",
  "period_days": 30,
  "total_predictions": 15,
  "outcomes": {
    "win": 9,
    "loss": 4,
    "break_even": 1,
    "active": 1
  },
  "metrics": {
    "win_rate": 64.3,
    "avg_accuracy_score": 72.5,
    "avg_rr_achieved": 1.8,
    "best_symbol": "BTCUSDT",
    "worst_symbol": "DOGEUSDT"
  },
  "insights": [
    "SL-Abstände könnten um 0.5% erweitert werden - 3 Trades wurden knapp ausgestoppt",
    "Volume-Confirmation erhöht Win-Rate um 15%"
  ]
}
```

---

## Scoring System

### Accuracy Score Berechnung (0-100)

```python
def calculate_accuracy_score(prediction: Prediction, outcome: str) -> float:
    score = 0
    
    # Direction correct (40 points max)
    if outcome == "win":
        score += 40
    elif outcome == "break_even":
        score += 20
    
    # Entry timing (20 points max)
    # Wie nah war Entry am optimalen Punkt?
    entry_efficiency = calculate_entry_efficiency(prediction)
    score += entry_efficiency * 20
    
    # Risk/Reward achieved (20 points max)
    rr_achieved = calculate_rr_achieved(prediction)
    if rr_achieved >= 2.0:
        score += 20
    elif rr_achieved >= 1.5:
        score += 15
    elif rr_achieved >= 1.0:
        score += 10
    
    # Timing bonus (20 points max)
    # Hit target before expiry? How quickly?
    timing_bonus = calculate_timing_bonus(prediction)
    score += timing_bonus * 20
    
    return min(100, max(0, score))
```

---

## Global Insights Generation

Regelbasierte Erkennung von Mustern über alle Predictions:

```python
def generate_global_insights(user_id: str) -> List[GlobalInsight]:
    insights = []
    predictions = get_recent_predictions(user_id, days=30)
    
    # Pattern: SL zu eng (>30% ausgestoppt vor TP)
    stopped_out_early = [p for p in predictions 
                        if p.outcome == "loss" and p.mae < abs(p.stop_loss - p.entry)]
    if len(stopped_out_early) / len(predictions) > 0.3:
        insights.append(GlobalInsight(
            type="sl_too_tight",
            description="SL-Abstände sind oft zu eng - erweitere um 0.3-0.5%",
            confidence=len(stopped_out_early) / len(predictions),
            applies_to_all=True
        ))
    
    # Pattern: Bestimmte Timeframes erfolgreicher
    by_timeframe = group_by(predictions, "timeframe")
    best_tf = max(by_timeframe, key=lambda tf: win_rate(by_timeframe[tf]))
    if win_rate(by_timeframe[best_tf]) > win_rate(predictions) + 10:
        insights.append(GlobalInsight(
            type="timeframe_preference",
            description=f"{best_tf} Timeframe hat +10% bessere Win-Rate",
            confidence=0.8,
            applies_to_all=False,
            source_strategy=None  # Gilt für alle
        ))
    
    return insights
```

---

## Token-Budget für Feedback-Kontext

**Ziel:** Max ~200 Tokens für Feedback-Injection

**Template:**
```
[DEIN PERFORMANCE FEEDBACK - {strategy_type}]
Letzte 10 {strategy_type}: {win_rate}% Win, Score Ø{avg_score}
Stärken: {strengths}
Schwächen: {weaknesses}
Tipp: {top_insight}
```

**Beispiel (~150 Tokens):**
```
[DEIN PERFORMANCE FEEDBACK - breakout_pullback]
Letzte 10 Breakout-Pullback: 70% Win, Score Ø75
Stärken: Gute Entry-Timing bei Volume-Confirmation, TP1 meist erreicht
Schwächen: SL 3x zu eng vor TP getroffen
Tipp: Erweitere SL um 0.3% bei High-Volatility Coins
```

---

## Dateien zu erstellen/ändern

| Datei | Aktion | Beschreibung |
|-------|--------|--------------|
| `backend/app/models/database.py` | Ändern | +Prediction, +PredictionEvaluation, +GlobalInsight |
| `src/intent_router.py` | Ändern | +StrategyType, +classify_strategy() |
| `backend/app/core/repositories.py` | Ändern | +PredictionRepository |
| `backend/app/services/prediction_service.py` | Neu | Prediction lifecycle management |
| `backend/app/services/feedback_context.py` | Neu | Token-efficient context generation |
| `backend/app/services/evaluation_scheduler.py` | Neu | Background evaluation task |
| `backend/app/api/routes/predictions.py` | Neu | REST API für Predictions |
| `backend/app/services/agent_service.py` | Ändern | Strategy classification + feedback injection |
| `tests/test_prediction_service.py` | Neu | Unit tests |
| `tests/test_intent_router_strategy.py` | Neu | Strategy classification tests |

---

## Zukunft: ML-basiertes Learning (Phase 8+)

Nach Sammlung von ausreichend Daten (~100+ Predictions pro Strategie):

1. **Feature Engineering:** Entry-Bedingungen, Markt-Kontext, Indicator-Werte als Features
2. **Model Training:** Classifier für Prediction-Qualität
3. **Confidence Calibration:** ML-basierte Confidence statt regelbasiert
4. **Automatische Insight-Generierung:** Clustering von erfolgreichen Setups

---

## Abhängigkeiten

- Phase 6 (Multi-User) ✅ – User-Scoping für Predictions
- `src/exchange_tools.py` – Marktdaten für Evaluation
- `src/intent_router.py` – Basis für Strategie-Klassifizierung
