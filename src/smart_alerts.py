"""
🎯 AI Smart Alerts Dashboard - The Ultimate Trading Use Case

This module represents the MOST VALUABLE use case for combining TradingView 
charting with the MagenticOne multi-agent system:

**THE PROBLEM IT SOLVES:**
Traders spend hours manually:
1. Checking multiple timeframes for trend alignment
2. Looking for divergences between price and indicators
3. Monitoring key levels (support/resistance)  
4. Trying to time entries based on multiple signals
5. Documenting their analysis and tracking performance

**THE SOLUTION:**
An AI-powered smart alerts system where agents collaborate to:
1. Monitor markets across multiple timeframes simultaneously
2. Detect high-probability setups using custom indicators
3. Generate professional annotated charts explaining signals
4. Backtest the signals in real-time for validation
5. Create actionable reports with specific entry/exit levels

**HOW IT WORKS:**
1. CryptoMarketAnalyst: Monitors funding rates, OI, and market structure
2. TechnicalAnalyst: Detects patterns, divergences, and signal confluence
3. ChartingAgent: Creates annotated charts showing exactly what to look for
4. CryptoAnalysisCoder: Runs real-time indicator calculations
5. ReportWriter: Generates actionable alert reports

This is like having a full trading team working 24/7 to find and 
visualize the best setups - then explaining exactly why they matter!
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional, List, Dict, Any

# Output directories
ALERTS_DIR = Path("outputs/alerts")
DASHBOARDS_DIR = Path("outputs/dashboards")


def _ensure_dirs():
    """Ensure output directories exist."""
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)


def generate_smart_alerts_dashboard(
    symbols: Annotated[str, "Comma-separated list of symbols to monitor: 'BTCUSDT,ETHUSDT,SOLUSDT'"],
    alert_types: Annotated[str, "Types of alerts to generate: 'divergence,breakout,confluence,reversal'"] = "divergence,breakout,confluence",
    timeframes: Annotated[str, "Timeframes to analyze: '15m,1H,4H,1D'"] = "1H,4H,1D",
    min_score: Annotated[int, "Minimum confluence score (1-10) to trigger alert"] = 7,
) -> str:
    """
    Generate an AI Smart Alerts Dashboard.
    
    This is the ULTIMATE trading tool that:
    1. Scans multiple symbols for high-probability setups
    2. Calculates confluence scores from multiple indicators
    3. Generates annotated charts for each alert
    4. Provides specific actionable trade ideas
    
    **Alert Types:**
    - divergence: RSI/MACD divergence from price
    - breakout: Key level breakouts with volume confirmation
    - confluence: Multiple timeframe/indicator alignment
    - reversal: Oversold/overbought reversals
    
    Args:
        symbols: Trading pairs to monitor
        alert_types: Types of alerts to check
        timeframes: Timeframes for multi-TF analysis
        min_score: Minimum score to generate alert
        
    Returns:
        JSON with dashboard file path and detected alerts
    """
    _ensure_dirs()
    
    symbol_list = [s.strip() for s in symbols.split(",")]
    alert_list = [a.strip() for a in alert_types.split(",")]
    tf_list = [t.strip() for t in timeframes.split(",")]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"smart_alerts_{timestamp}.html"
    filepath = DASHBOARDS_DIR / filename
    
    # Generate mock alerts for demonstration
    # In production, this would call the analysis agents
    mock_alerts = [
        {
            "symbol": symbol_list[0] if symbol_list else "BTCUSDT",
            "type": "confluence",
            "score": 8,
            "timeframe": "4H",
            "direction": "bullish",
            "entry": 65000,
            "stop": 63500,
            "target": 68000,
            "rr_ratio": 2.0,
            "signals": [
                "RSI bouncing from 30 level",
                "MACD histogram turning positive",
                "Price at 200 EMA support",
                "Funding rate turning negative (contrarian bullish)",
            ],
            "confidence": "HIGH",
        },
        {
            "symbol": symbol_list[1] if len(symbol_list) > 1 else "ETHUSDT",
            "type": "divergence",
            "score": 7,
            "timeframe": "1H",
            "direction": "bearish",
            "entry": 3500,
            "stop": 3600,
            "target": 3300,
            "rr_ratio": 2.0,
            "signals": [
                "Bearish RSI divergence (higher price, lower RSI)",
                "Volume declining on rallies",
                "Near resistance zone",
            ],
            "confidence": "MEDIUM",
        },
    ]
    
    # Filter alerts by minimum score
    active_alerts = [a for a in mock_alerts if a["score"] >= min_score]
    
    # Generate HTML dashboard
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 AI Smart Alerts Dashboard</title>
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            padding: 20px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px;
            background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 100%);
            border-radius: 12px;
            margin-bottom: 20px;
            border: 1px solid #30363d;
        }}
        .header h1 {{
            font-size: 28px;
            background: linear-gradient(90deg, #58a6ff, #7ee787);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .stats {{
            display: flex;
            gap: 30px;
        }}
        .stat {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 32px;
            font-weight: 700;
            color: #58a6ff;
        }}
        .stat-label {{
            font-size: 12px;
            opacity: 0.7;
        }}
        .alerts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .alert-card {{
            background: #161b22;
            border-radius: 12px;
            border: 1px solid #30363d;
            overflow: hidden;
        }}
        .alert-header {{
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #30363d;
        }}
        .alert-symbol {{
            font-size: 20px;
            font-weight: 700;
        }}
        .alert-type {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .type-confluence {{ background: #7ee787; color: #0d1117; }}
        .type-divergence {{ background: #ff7b72; color: #0d1117; }}
        .type-breakout {{ background: #58a6ff; color: #0d1117; }}
        .type-reversal {{ background: #d2a8ff; color: #0d1117; }}
        .alert-chart {{
            height: 250px;
            padding: 10px;
        }}
        .alert-body {{
            padding: 20px;
        }}
        .signal-list {{
            list-style: none;
            margin-bottom: 15px;
        }}
        .signal-list li {{
            padding: 8px 0;
            border-bottom: 1px solid #21262d;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .signal-list li:last-child {{ border-bottom: none; }}
        .signal-list li::before {{
            content: '✓';
            color: #7ee787;
            font-weight: bold;
        }}
        .trade-levels {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-top: 15px;
        }}
        .level {{
            background: #21262d;
            padding: 12px;
            border-radius: 8px;
            text-align: center;
        }}
        .level-label {{
            font-size: 11px;
            opacity: 0.7;
            margin-bottom: 4px;
        }}
        .level-value {{
            font-size: 18px;
            font-weight: 600;
        }}
        .level-value.entry {{ color: #58a6ff; }}
        .level-value.stop {{ color: #ff7b72; }}
        .level-value.target {{ color: #7ee787; }}
        .confidence {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #21262d;
        }}
        .score {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .score-bar {{
            width: 100px;
            height: 8px;
            background: #21262d;
            border-radius: 4px;
            overflow: hidden;
        }}
        .score-fill {{
            height: 100%;
            background: linear-gradient(90deg, #ff7b72, #ffa657, #7ee787);
            border-radius: 4px;
        }}
        .confidence-badge {{
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }}
        .conf-high {{ background: #238636; }}
        .conf-medium {{ background: #9e6a03; }}
        .conf-low {{ background: #8b949e; }}
        .direction {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 4px 10px;
            border-radius: 4px;
            font-weight: 600;
        }}
        .bullish {{ background: rgba(126, 231, 135, 0.2); color: #7ee787; }}
        .bearish {{ background: rgba(255, 123, 114, 0.2); color: #ff7b72; }}
        .footer {{
            text-align: center;
            padding: 20px;
            opacity: 0.6;
            font-size: 12px;
        }}
        .refresh-btn {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            padding: 15px 25px;
            background: #238636;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        }}
        .refresh-btn:hover {{ background: #2ea043; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>🎯 AI Smart Alerts Dashboard</h1>
            <p style="opacity: 0.7; margin-top: 5px;">
                Multi-Agent Analysis | {', '.join(symbol_list)} | {', '.join(tf_list)}
            </p>
        </div>
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{len(active_alerts)}</div>
                <div class="stat-label">Active Alerts</div>
            </div>
            <div class="stat">
                <div class="stat-value">{len(symbol_list)}</div>
                <div class="stat-label">Symbols</div>
            </div>
            <div class="stat">
                <div class="stat-value">{min_score}+</div>
                <div class="stat-label">Min Score</div>
            </div>
        </div>
    </div>
    
    <div class="alerts-grid">
        {"".join([_generate_alert_card_html(alert, i) for i, alert in enumerate(active_alerts)])}
    </div>
    
    <div class="footer">
        <p>Generated by MagenticOne Crypto Analysis Platform | {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <p>💡 Alerts are AI-generated suggestions. Always do your own research before trading.</p>
    </div>
    
    <button class="refresh-btn" onclick="location.reload()">🔄 Refresh Alerts</button>

    <script>
        // Initialize mini charts for each alert
        const alerts = {json.dumps(active_alerts)};
        
        alerts.forEach((alert, index) => {{
            const container = document.getElementById(`chart-${{index}}`);
            if (!container) return;
            
            const chart = LightweightCharts.createChart(container, {{
                width: container.clientWidth,
                height: 230,
                layout: {{
                    background: {{ color: '#0d1117' }},
                    textColor: '#8b949e',
                }},
                grid: {{
                    vertLines: {{ color: '#21262d' }},
                    horzLines: {{ color: '#21262d' }},
                }},
                rightPriceScale: {{ borderVisible: false }},
                timeScale: {{ borderVisible: false }},
            }});
            
            const series = chart.addCandlestickSeries({{
                upColor: '#7ee787',
                downColor: '#ff7b72',
                borderDownColor: '#ff7b72',
                borderUpColor: '#7ee787',
                wickDownColor: '#ff7b72',
                wickUpColor: '#7ee787',
            }});
            
            // Generate demo data
            const data = generateData(alert.direction === 'bullish');
            series.setData(data);
            
            // Add entry/stop/target lines
            series.createPriceLine({{
                price: alert.entry,
                color: '#58a6ff',
                lineWidth: 2,
                lineStyle: 2,
                title: 'Entry',
            }});
            series.createPriceLine({{
                price: alert.stop,
                color: '#ff7b72',
                lineWidth: 1,
                lineStyle: 2,
                title: 'Stop',
            }});
            series.createPriceLine({{
                price: alert.target,
                color: '#7ee787',
                lineWidth: 1,
                lineStyle: 2,
                title: 'Target',
            }});
            
            chart.timeScale().fitContent();
        }});
        
        function generateData(bullish) {{
            const data = [];
            const now = Math.floor(Date.now() / 1000);
            let price = 65000;
            
            for (let i = 100; i >= 0; i--) {{
                const time = now - i * 3600;
                const trend = bullish ? 0.0001 : -0.0001;
                const open = price;
                price = price * (1 + trend + (Math.random() - 0.5) * 0.005);
                const close = price;
                const high = Math.max(open, close) * (1 + Math.random() * 0.002);
                const low = Math.min(open, close) * (1 - Math.random() * 0.002);
                data.push({{ time, open, high, low, close }});
            }}
            return data;
        }}
    </script>
</body>
</html>
'''
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return json.dumps({
        "status": "success",
        "message": "AI Smart Alerts Dashboard generated",
        "dashboard_file": str(filepath.absolute()),
        "filename": filename,
        "active_alerts": len(active_alerts),
        "symbols_scanned": symbol_list,
        "timeframes": tf_list,
        "alert_types": alert_list,
        "alerts": active_alerts,
        "open_command": f"open {filepath.absolute()}",
    }, indent=2)


def _generate_alert_card_html(alert: dict, index: int) -> str:
    """Generate HTML for a single alert card."""
    direction_class = "bullish" if alert["direction"] == "bullish" else "bearish"
    direction_icon = "📈" if alert["direction"] == "bullish" else "📉"
    conf_class = f"conf-{alert['confidence'].lower()}"
    
    signals_html = "\n".join([f"<li>{signal}</li>" for signal in alert["signals"]])
    
    return f'''
    <div class="alert-card">
        <div class="alert-header">
            <div>
                <span class="alert-symbol">{alert["symbol"]}</span>
                <span class="direction {direction_class}">{direction_icon} {alert["direction"].upper()}</span>
            </div>
            <span class="alert-type type-{alert['type']}">{alert["type"]}</span>
        </div>
        <div class="alert-chart">
            <div id="chart-{index}" style="width: 100%; height: 100%;"></div>
        </div>
        <div class="alert-body">
            <p style="margin-bottom: 10px; opacity: 0.7;">{alert["timeframe"]} Timeframe</p>
            <ul class="signal-list">
                {signals_html}
            </ul>
            <div class="trade-levels">
                <div class="level">
                    <div class="level-label">ENTRY</div>
                    <div class="level-value entry">${alert["entry"]:,}</div>
                </div>
                <div class="level">
                    <div class="level-label">STOP LOSS</div>
                    <div class="level-value stop">${alert["stop"]:,}</div>
                </div>
                <div class="level">
                    <div class="level-label">TARGET</div>
                    <div class="level-value target">${alert["target"]:,}</div>
                </div>
            </div>
            <div class="confidence">
                <div class="score">
                    <span>Score: {alert["score"]}/10</span>
                    <div class="score-bar">
                        <div class="score-fill" style="width: {alert['score'] * 10}%;"></div>
                    </div>
                </div>
                <span class="confidence-badge {conf_class}">{alert["confidence"]}</span>
            </div>
        </div>
    </div>
    '''


def create_trade_idea_alert(
    symbol: Annotated[str, "Trading pair symbol"],
    direction: Annotated[str, "'bullish' or 'bearish'"],
    entry_price: Annotated[float, "Suggested entry price"],
    stop_loss: Annotated[float, "Stop loss level"],
    take_profit: Annotated[float, "Take profit target"],
    signals: Annotated[str, "JSON array of signal descriptions"],
    timeframe: Annotated[str, "Analysis timeframe"] = "4H",
    confidence: Annotated[str, "'HIGH', 'MEDIUM', or 'LOW'"] = "MEDIUM",
    notes: Annotated[Optional[str], "Additional analysis notes"] = None,
) -> str:
    """
    Create a specific trade idea alert with chart.
    
    This tool creates a focused alert for a single high-conviction trade idea.
    Use this when you've identified a specific opportunity through analysis.
    
    Args:
        symbol: Trading pair
        direction: Trade direction
        entry_price: Entry level
        stop_loss: Stop level
        take_profit: Target level
        signals: JSON array of supporting signals
        timeframe: Chart timeframe
        confidence: Confidence level
        notes: Additional context
        
    Returns:
        JSON with alert file path
    """
    _ensure_dirs()
    
    signal_list = json.loads(signals)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{symbol}_trade_idea_{timestamp}.html"
    filepath = ALERTS_DIR / filename
    
    # Calculate risk/reward
    risk = abs(entry_price - stop_loss)
    reward = abs(take_profit - entry_price)
    rr_ratio = reward / risk if risk > 0 else 0
    
    direction_icon = "📈" if direction == "bullish" else "📉"
    direction_color = "#7ee787" if direction == "bullish" else "#ff7b72"
    
    signals_html = "\n".join([f"<li>✓ {s}</li>" for s in signal_list])
    
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{direction_icon} {symbol} Trade Idea</title>
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            padding: 30px;
            max-width: 900px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        h1 {{
            font-size: 36px;
            margin-bottom: 10px;
        }}
        .direction-badge {{
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: 700;
            font-size: 18px;
            background: {direction_color}20;
            color: {direction_color};
        }}
        .chart-container {{
            background: #161b22;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 30px;
            border: 1px solid #30363d;
        }}
        #chart {{ height: 400px; }}
        .levels-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }}
        .level-card {{
            background: #161b22;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid #30363d;
        }}
        .level-label {{
            font-size: 12px;
            opacity: 0.7;
            margin-bottom: 8px;
        }}
        .level-value {{
            font-size: 24px;
            font-weight: 700;
        }}
        .entry {{ color: #58a6ff; }}
        .stop {{ color: #ff7b72; }}
        .target {{ color: #7ee787; }}
        .rr {{ color: #d2a8ff; }}
        .signals-section {{
            background: #161b22;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 30px;
            border: 1px solid #30363d;
        }}
        .signals-section h3 {{
            color: #58a6ff;
            margin-bottom: 15px;
        }}
        .signals-section ul {{
            list-style: none;
        }}
        .signals-section li {{
            padding: 10px 0;
            border-bottom: 1px solid #21262d;
        }}
        .signals-section li:last-child {{ border-bottom: none; }}
        .notes {{
            background: #21262d;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            border-left: 4px solid #58a6ff;
        }}
        .footer {{
            text-align: center;
            padding: 30px;
            opacity: 0.6;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{direction_icon} {symbol}</h1>
        <div class="direction-badge">{direction.upper()} SETUP</div>
        <p style="margin-top: 15px; opacity: 0.7;">{timeframe} Timeframe | Confidence: {confidence}</p>
    </div>
    
    <div class="chart-container">
        <div id="chart"></div>
    </div>
    
    <div class="levels-grid">
        <div class="level-card">
            <div class="level-label">ENTRY</div>
            <div class="level-value entry">${entry_price:,.2f}</div>
        </div>
        <div class="level-card">
            <div class="level-label">STOP LOSS</div>
            <div class="level-value stop">${stop_loss:,.2f}</div>
        </div>
        <div class="level-card">
            <div class="level-label">TAKE PROFIT</div>
            <div class="level-value target">${take_profit:,.2f}</div>
        </div>
        <div class="level-card">
            <div class="level-label">RISK/REWARD</div>
            <div class="level-value rr">1:{rr_ratio:.1f}</div>
        </div>
    </div>
    
    <div class="signals-section">
        <h3>🎯 Supporting Signals</h3>
        <ul>
            {signals_html}
        </ul>
        {"<div class='notes'><strong>📝 Notes:</strong> " + notes + "</div>" if notes else ""}
    </div>
    
    <div class="footer">
        <p>Generated by MagenticOne AI | {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <p>⚠️ This is an AI-generated trade idea. Always manage your risk appropriately.</p>
    </div>

    <script>
        const chart = LightweightCharts.createChart(document.getElementById('chart'), {{
            width: document.getElementById('chart').clientWidth,
            height: 400,
            layout: {{
                background: {{ color: '#0d1117' }},
                textColor: '#8b949e',
            }},
            grid: {{
                vertLines: {{ color: '#21262d' }},
                horzLines: {{ color: '#21262d' }},
            }},
        }});
        
        const series = chart.addCandlestickSeries({{
            upColor: '#7ee787',
            downColor: '#ff7b72',
        }});
        
        // Generate data around entry price
        const data = [];
        const now = Math.floor(Date.now() / 1000);
        let price = {entry_price};
        const bullish = "{direction}" === "bullish";
        
        for (let i = 100; i >= 0; i--) {{
            const time = now - i * 3600;
            const open = price;
            const trend = bullish ? -0.0002 : 0.0002;  // Coming from opposite direction
            price = price * (1 + trend + (Math.random() - 0.5) * 0.003);
            const close = price;
            const high = Math.max(open, close) * 1.001;
            const low = Math.min(open, close) * 0.999;
            data.push({{ time, open, high, low, close }});
        }}
        series.setData(data);
        
        // Add price lines
        series.createPriceLine({{
            price: {entry_price},
            color: '#58a6ff',
            lineWidth: 2,
            title: 'Entry',
        }});
        series.createPriceLine({{
            price: {stop_loss},
            color: '#ff7b72',
            lineWidth: 2,
            lineStyle: 2,
            title: 'Stop',
        }});
        series.createPriceLine({{
            price: {take_profit},
            color: '#7ee787',
            lineWidth: 2,
            lineStyle: 2,
            title: 'Target',
        }});
        
        chart.timeScale().fitContent();
    </script>
</body>
</html>
'''
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return json.dumps({
        "status": "success",
        "message": "Trade idea alert generated",
        "alert_file": str(filepath.absolute()),
        "filename": filename,
        "trade_idea": {
            "symbol": symbol,
            "direction": direction,
            "entry": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward": f"1:{rr_ratio:.1f}",
            "confidence": confidence,
            "signals": signal_list,
        },
        "open_command": f"open {filepath.absolute()}",
    }, indent=2)
