"""
TradingView Chart Tools for MagenticOne

This module provides tools for generating professional TradingView-style charts
using the TradingView Charting Library concepts. It creates interactive HTML charts
that can be opened in a browser with advanced charting capabilities.

Key Features:
- Generate professional candlestick charts with TradingView styling
- Add custom indicators from the indicator registry
- Support for multiple timeframes and drawing tools
- Export charts as HTML files or serve via local web server
- AI-powered chart annotations and analysis markers
- **Entry/Exit point visualization with signals**
- **Support/Resistance level drawing**
- **Trade setup annotations**
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional, List, Dict, Any
import pandas as pd

from chart_assets import LIGHTWEIGHT_CHARTS_SCRIPT

# Get project root directory (parent of src/)
_PROJECT_ROOT = Path(__file__).parent.parent.resolve()


# =============================================================================
# ANNOTATION TYPES FOR CHART MARKERS
# =============================================================================
# These define the structure for various chart annotations that agents can create

ANNOTATION_TYPES = {
    "entry_long": {"shape": "arrowUp", "position": "belowBar", "color": "#26a69a", "text": "▲ LONG"},
    "entry_short": {"shape": "arrowDown", "position": "aboveBar", "color": "#ef5350", "text": "▼ SHORT"},
    "exit_long": {"shape": "circle", "position": "aboveBar", "color": "#26a69a", "text": "✓ TP"},
    "exit_short": {"shape": "circle", "position": "belowBar", "color": "#ef5350", "text": "✓ TP"},
    "stop_loss": {"shape": "square", "position": "belowBar", "color": "#ff5722", "text": "✗ SL"},
    "take_profit": {"shape": "square", "position": "aboveBar", "color": "#4caf50", "text": "TP"},
    "support": {"shape": "circle", "position": "belowBar", "color": "#2196f3", "text": "S"},
    "resistance": {"shape": "circle", "position": "aboveBar", "color": "#9c27b0", "text": "R"},
    "buy_signal": {"shape": "arrowUp", "position": "belowBar", "color": "#00e676", "text": "BUY"},
    "sell_signal": {"shape": "arrowDown", "position": "aboveBar", "color": "#ff1744", "text": "SELL"},
    "warning": {"shape": "circle", "position": "aboveBar", "color": "#ffc107", "text": "⚠"},
    "info": {"shape": "circle", "position": "aboveBar", "color": "#03a9f4", "text": "ℹ"},
}

# Output directory for charts - use absolute path to project root
CHART_OUTPUT_DIR = _PROJECT_ROOT / "outputs" / "charts"


def _ensure_output_dir():
    """Ensure the chart output directory exists."""
    CHART_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_tradingview_chart(
    symbol: Annotated[str, "Trading pair symbol (e.g., 'BTCUSDT', 'ETHUSDT')"],
    interval: Annotated[str, "Chart interval: '1m', '5m', '15m', '1H', '4H', '1D', '1W'"] = "1H",
    indicators: Annotated[Optional[str], "Comma-separated list of indicators: 'rsi', 'macd', 'bollinger', 'sma', 'ema', 'volume', 'sar'"] = "volume",
    theme: Annotated[str, "Chart theme: 'dark' or 'light'"] = "dark",
    title: Annotated[Optional[str], "Optional chart title"] = None,
    annotations: Annotated[Optional[str], "JSON string of chart annotations/markers to add (e.g., entry/exit points, support/resistance levels)"] = None,
) -> str:
    """
    Generate a professional TradingView-style interactive chart.
    
    Creates an HTML file with a fully interactive chart using Lightweight Charts
    (TradingView's open-source charting library). The chart includes:
    - Professional candlestick display
    - Technical indicators
    - Interactive zoom/pan
    - Crosshair with price/time display
    - Dark/light theme support
    
    Args:
        symbol: The trading pair to chart
        interval: Timeframe for the chart
        indicators: Comma-separated indicator list
        theme: Chart color theme
        title: Optional chart title
        annotations: JSON markers/annotations
        
    Returns:
        JSON string with chart file path and URL
    """
    try:
        _ensure_output_dir()
        
        # Parse indicators
        indicator_list = [i.strip().lower() for i in indicators.split(",")] if indicators else []
        
        # Generate timestamp for unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chart_title = title or f"{symbol} {interval} Chart"
        filename = f"{symbol}_{interval}_{timestamp}.html"
        filepath = CHART_OUTPUT_DIR / filename
        data_source = "placeholder"  # Will be updated if real data is fetched
        
        # Try to fetch real OHLCV data from exchange
        real_data = None
        try:
            from exchange_tools import get_ohlcv_data
            
            # Map interval to exchange format
            interval_map = {
                "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                "1H": "1h", "1h": "1h", "4H": "4h", "4h": "4h",
                "1D": "1d", "1d": "1d", "1W": "1w", "1w": "1w",
            }
            exchange_interval = interval_map.get(interval, "1h")
            
            result = json.loads(get_ohlcv_data(symbol, exchange_interval, limit=200))
            
            # Handle both "data" and "candles" keys in response
            bars = result.get("data") or result.get("candles")
            if bars:
                real_data = {
                    "candles": [
                        {
                            "time": int(datetime.fromisoformat(b["timestamp"].replace("Z", "+00:00")).timestamp()) if isinstance(b["timestamp"], str) else int(b["timestamp"]) // 1000,
                            "open": float(b["open"]),
                            "high": float(b["high"]),
                            "low": float(b["low"]),
                            "close": float(b["close"]),
                        }
                        for b in bars
                    ],
                    "volumes": [
                        {
                            "time": int(datetime.fromisoformat(b["timestamp"].replace("Z", "+00:00")).timestamp()) if isinstance(b["timestamp"], str) else int(b["timestamp"]) // 1000,
                            "value": float(b["volume"]),
                            "color": "#26a69a" if float(b["close"]) >= float(b["open"]) else "#ef5350",
                        }
                        for b in bars
                    ],
                }
                data_source = f"Bitget ({len(bars)} bars)"
        except Exception as e:
            # Fall back to placeholder data if exchange fetch fails
            pass
        
        # Parse annotations if provided
        chart_annotations = []
        if annotations:
            try:
                chart_annotations = json.loads(annotations)
            except json.JSONDecodeError:
                pass
        
        # Theme colors
        if theme == "dark":
            bg_color = "#1e222d"
            text_color = "#d1d4dc"
            grid_color = "#2a2e39"
            up_color = "#26a69a"
            down_color = "#ef5350"
        else:
            bg_color = "#ffffff"
            text_color = "#131722"
            grid_color = "#e1e3eb"
            up_color = "#26a69a"
            down_color = "#ef5350"
        
        # Build indicator panels HTML
        indicator_panels = ""
        indicator_scripts = ""
        panel_count = 1
        
        if "rsi" in indicator_list:
            panel_count += 1
            indicator_panels += f'''
            <div id="rsi-container" style="width: 100%; height: 150px; margin-top: 10px;"></div>
            '''
            indicator_scripts += '''
            // RSI Panel
            const rsiChart = LightweightCharts.createChart(document.getElementById('rsi-container'), {
                width: container.clientWidth,
                height: 150,
                layout: { background: { color: '${bg_color}' }, textColor: '${text_color}' },
                grid: { vertLines: { color: '${grid_color}' }, horzLines: { color: '${grid_color}' } },
                rightPriceScale: { scaleMargins: { top: 0.1, bottom: 0.1 } },
            });
            const rsiSeries = rsiChart.addLineSeries({ color: '#7b1fa2', lineWidth: 2 });
            // RSI data will be calculated from main data
            '''
        
        if "macd" in indicator_list:
            panel_count += 1
            indicator_panels += f'''
            <div id="macd-container" style="width: 100%; height: 150px; margin-top: 10px;"></div>
            '''
        
        # Create the HTML chart file
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{chart_title}</title>
    {LIGHTWEIGHT_CHARTS_SCRIPT}
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: {bg_color};
            color: {text_color};
            padding: 20px;
        }}
        .chart-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid {grid_color};
            margin-bottom: 10px;
        }}
        .chart-title {{
            font-size: 24px;
            font-weight: 600;
        }}
        .chart-info {{
            font-size: 14px;
            opacity: 0.7;
        }}
        .chart-container {{
            width: 100%;
            height: calc(100vh - 150px);
            min-height: 500px;
        }}
        .indicator-panel {{
            width: 100%;
            margin-top: 10px;
        }}
        .legend {{
            position: absolute;
            left: 12px;
            top: 12px;
            z-index: 1;
            font-size: 14px;
            font-family: sans-serif;
            line-height: 18px;
            font-weight: 300;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 4px 0;
        }}
        .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: 2px;
        }}
        .toolbar {{
            display: flex;
            gap: 10px;
            padding: 10px 0;
        }}
        .toolbar button {{
            padding: 8px 16px;
            background: {grid_color};
            border: none;
            border-radius: 4px;
            color: {text_color};
            cursor: pointer;
            font-size: 14px;
        }}
        .toolbar button:hover {{
            background: {up_color};
            color: white;
        }}
        .toolbar button.active {{
            background: {up_color};
            color: white;
        }}
        .analysis-panel {{
            background: {grid_color};
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
        }}
        .analysis-panel h3 {{
            margin-bottom: 10px;
            color: {up_color};
        }}
        .signal {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            font-weight: 600;
            margin-right: 10px;
        }}
        .signal.bullish {{ background: {up_color}; color: white; }}
        .signal.bearish {{ background: {down_color}; color: white; }}
        .signal.neutral {{ background: #888; color: white; }}
    </style>
</head>
<body>
    <div class="chart-header">
        <div>
            <div class="chart-title">📊 {chart_title}</div>
            <div class="chart-info">Interval: {interval} | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | MagenticOne Analysis</div>
        </div>
        <div class="toolbar">
            <button onclick="setInterval('1m')">1m</button>
            <button onclick="setInterval('5m')">5m</button>
            <button onclick="setInterval('15m')">15m</button>
            <button onclick="setInterval('1H')" class="{'active' if interval == '1H' else ''}">1H</button>
            <button onclick="setInterval('4H')">4H</button>
            <button onclick="setInterval('1D')">1D</button>
        </div>
    </div>
    
    <div id="chart-container" class="chart-container"></div>
    
    {indicator_panels}
    
    <div id="analysis-panel" class="analysis-panel" style="display: none;">
        <h3>🎯 AI Analysis</h3>
        <div id="analysis-content"></div>
    </div>

    <script>
        const container = document.getElementById('chart-container');
        
        // Create the main chart with autoSize for iframe compatibility
        const chart = LightweightCharts.createChart(container, {{
            autoSize: true,
            layout: {{
                background: {{ color: '{bg_color}' }},
                textColor: '{text_color}',
            }},
            grid: {{
                vertLines: {{ color: '{grid_color}' }},
                horzLines: {{ color: '{grid_color}' }},
            }},
            crosshair: {{
                mode: LightweightCharts.CrosshairMode.Normal,
            }},
            rightPriceScale: {{
                borderColor: '{grid_color}',
            }},
            timeScale: {{
                borderColor: '{grid_color}',
                timeVisible: true,
                secondsVisible: false,
            }},
        }});

        // Add candlestick series
        const candlestickSeries = chart.addCandlestickSeries({{
            upColor: '{up_color}',
            downColor: '{down_color}',
            borderDownColor: '{down_color}',
            borderUpColor: '{up_color}',
            wickDownColor: '{down_color}',
            wickUpColor: '{up_color}',
        }});

        // Volume series (if enabled) - positioned at bottom 20% of chart on separate scale
        {'const volumeSeries = chart.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "volume" }); chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });' if 'volume' in indicator_list else ''}

        // Symbol-based price ranges for realistic placeholder data
        const symbolPrices = {{
            'BTCUSDT': {{ base: 65000, volatility: 500 }},
            'ETHUSDT': {{ base: 3500, volatility: 50 }},
            'SOLUSDT': {{ base: 150, volatility: 3 }},
            'SUIUSDT': {{ base: 3.5, volatility: 0.08 }},
            'BNBUSDT': {{ base: 600, volatility: 10 }},
            'XRPUSDT': {{ base: 0.6, volatility: 0.02 }},
            'DOGEUSDT': {{ base: 0.15, volatility: 0.005 }},
            'ADAUSDT': {{ base: 0.45, volatility: 0.01 }},
            'AVAXUSDT': {{ base: 35, volatility: 0.8 }},
            'LINKUSDT': {{ base: 15, volatility: 0.3 }},
        }};
        
        // Get price range for this symbol
        const symbolConfig = symbolPrices['{symbol}'] || {{ base: 100, volatility: 2 }};
        
        // Generate placeholder OHLCV data with correct price scale
        function generatePlaceholderData() {{
            const candles = [];
            const volumes = [];
            const now = Math.floor(Date.now() / 1000);
            let price = symbolConfig.base * (0.95 + Math.random() * 0.1);
            const vol = symbolConfig.volatility;
            
            for (let i = 200; i >= 0; i--) {{
                const time = now - i * 3600;
                const open = price;
                const change = (Math.random() - 0.5) * vol * 2;
                const close = open + change;
                const high = Math.max(open, close) + Math.random() * vol * 0.3;
                const low = Math.min(open, close) - Math.random() * vol * 0.3;
                // Scale volume appropriately (smaller for low-price assets)
                const baseVol = symbolConfig.base > 100 ? 50000 : (symbolConfig.base > 10 ? 200000 : 1000000);
                const volume = Math.random() * baseVol;
                
                candles.push({{ time, open, high, low, close }});
                volumes.push({{ time, value: volume, color: close >= open ? '{up_color}' : '{down_color}' }});
                price = close;
            }}
            
            return {{ candles, volumes }};
        }}

        // Calculate SMA
        function calculateSMA(data, period) {{
            const sma = [];
            for (let i = period - 1; i < data.length; i++) {{
                let sum = 0;
                for (let j = 0; j < period; j++) {{
                    sum += data[i - j].close;
                }}
                sma.push({{ time: data[i].time, value: sum / period }});
            }}
            return sma;
        }}

        // Calculate EMA
        function calculateEMA(data, period) {{
            const ema = [];
            const multiplier = 2 / (period + 1);
            let emaPrev = data.slice(0, period).reduce((sum, d) => sum + d.close, 0) / period;
            
            for (let i = period - 1; i < data.length; i++) {{
                const emaValue = (data[i].close - emaPrev) * multiplier + emaPrev;
                ema.push({{ time: data[i].time, value: emaValue }});
                emaPrev = emaValue;
            }}
            return ema;
        }}

        // Calculate Bollinger Bands
        function calculateBollingerBands(data, period, stdDev) {{
            const upper = [];
            const lower = [];
            
            for (let i = period - 1; i < data.length; i++) {{
                let sum = 0;
                for (let j = 0; j < period; j++) {{
                    sum += data[i - j].close;
                }}
                const sma = sum / period;
                
                let variance = 0;
                for (let j = 0; j < period; j++) {{
                    variance += Math.pow(data[i - j].close - sma, 2);
                }}
                const std = Math.sqrt(variance / period);
                
                upper.push({{ time: data[i].time, value: sma + stdDev * std }});
                lower.push({{ time: data[i].time, value: sma - stdDev * std }});
            }}
            
            return {{ upper, lower }};
        }}

        // Calculate Parabolic SAR
        function calculateSAR(data, acceleration = 0.02, maximum = 0.2) {{
            const sar = [];
            if (data.length < 2) return sar;
            
            let isUpTrend = data[1].close > data[0].close;
            let ep = isUpTrend ? data[0].high : data[0].low;
            let af = acceleration;
            let sarValue = isUpTrend ? data[0].low : data[0].high;
            
            for (let i = 1; i < data.length; i++) {{
                const prev = data[i - 1];
                const curr = data[i];
                
                // Calculate new SAR
                sarValue = sarValue + af * (ep - sarValue);
                
                // Check for trend reversal
                if (isUpTrend) {{
                    if (curr.low < sarValue) {{
                        isUpTrend = false;
                        sarValue = ep;
                        ep = curr.low;
                        af = acceleration;
                    }} else {{
                        if (curr.high > ep) {{
                            ep = curr.high;
                            af = Math.min(af + acceleration, maximum);
                        }}
                        sarValue = Math.min(sarValue, prev.low, curr.low);
                    }}
                }} else {{
                    if (curr.high > sarValue) {{
                        isUpTrend = true;
                        sarValue = ep;
                        ep = curr.high;
                        af = acceleration;
                    }} else {{
                        if (curr.low < ep) {{
                            ep = curr.low;
                            af = Math.min(af + acceleration, maximum);
                        }}
                        sarValue = Math.max(sarValue, prev.high, curr.high);
                    }}
                }}
                
                sar.push({{ 
                    time: curr.time, 
                    value: sarValue,
                    color: isUpTrend ? '#26a69a' : '#ef5350'
                }});
            }}
            return sar;
        }}

        // Interval switching - communicate with parent frame
        function setInterval(newInterval) {{
            console.log('Switching to interval:', newInterval);
            // Update button active state
            document.querySelectorAll('.toolbar button').forEach(btn => {{
                btn.classList.remove('active');
                if (btn.textContent === newInterval) {{
                    btn.classList.add('active');
                }}
            }});
            // Send message to parent window (web app)
            if (window.parent !== window) {{
                window.parent.postMessage({{
                    type: 'CHART_INTERVAL_CHANGE',
                    symbol: '{symbol}',
                    interval: newInterval
                }}, '*');
            }}
        }}

        // Load data and set chart series
        const realData = {json.dumps(real_data) if real_data else 'null'};
        const chartData = realData || generatePlaceholderData();
        candlestickSeries.setData(chartData.candles);
        {'volumeSeries.setData(chartData.volumes);' if 'volume' in indicator_list else ''}

        // Add SMA if enabled
        {'const sma20Series = chart.addLineSeries({ color: "#2196F3", lineWidth: 2 }); sma20Series.setData(calculateSMA(chartData.candles, 20));' if 'sma' in indicator_list else ''}
        
        // Add EMA if enabled
        {'const ema20Series = chart.addLineSeries({ color: "#FF9800", lineWidth: 2 }); ema20Series.setData(calculateEMA(chartData.candles, 20));' if 'ema' in indicator_list else ''}

        // Add Bollinger Bands if enabled
        {'const bbUpper = chart.addLineSeries({ color: "#9C27B0", lineWidth: 1 }); const bbLower = chart.addLineSeries({ color: "#9C27B0", lineWidth: 1 }); const bb = calculateBollingerBands(chartData.candles, 20, 2); bbUpper.setData(bb.upper); bbLower.setData(bb.lower);' if 'bollinger' in indicator_list else ''}

        // Add Parabolic SAR if enabled
        {'const sarData = calculateSAR(chartData.candles); const sarSeries = chart.addLineSeries({ lineWidth: 0, lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false }); sarSeries.setData(sarData.map(s => ({ time: s.time, value: s.value }))); sarSeries.setMarkers(sarData.map(s => ({ time: s.time, position: s.color === "#26a69a" ? "belowBar" : "aboveBar", color: s.color, shape: "circle", size: 0.5 })));' if 'sar' in indicator_list else ''}

        // Add markers/annotations if provided
        const annotations = {json.dumps(chart_annotations)};
        if (annotations.length > 0) {{
            candlestickSeries.setMarkers(annotations.map(a => ({{
                time: a.time,
                position: a.position || 'aboveBar',
                color: a.color || '{up_color}',
                shape: a.shape || 'circle',
                text: a.text || '',
            }})));
        }}

        // Fit content after a short delay to ensure layout is ready
        setTimeout(() => {{
            chart.timeScale().fitContent();
        }}, 100);
    </script>
</body>
</html>
'''
        
        # Write the HTML file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        return json.dumps({
            "status": "success",
            "message": f"TradingView chart generated successfully",
            "chart_file": str(filepath.absolute()),
            "filename": filename,
            "symbol": symbol,
            "interval": interval,
            "indicators": indicator_list,
            "theme": theme,
            "open_command": f"open {filepath.absolute()}",
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to generate chart: {str(e)}",
        })


def create_ai_annotated_chart(
    symbol: Annotated[str, "Trading pair symbol (e.g., 'BTCUSDT')"],
    analysis_signals: Annotated[str, "JSON array of trading signals with time, type, and description"],
    support_resistance: Annotated[Optional[str], "JSON array of support/resistance levels"] = None,
    trend_lines: Annotated[Optional[str], "JSON array of trend line definitions"] = None,
    interval: Annotated[str, "Chart interval"] = "1H",
) -> str:
    """
    Create a chart with AI-powered annotations and trading signals.
    
    Generates a professional chart with:
    - Buy/Sell signal markers from AI analysis
    - Support and resistance level lines
    - Trend lines and pattern annotations
    - Custom indicator signals
    
    Args:
        symbol: Trading pair to chart
        analysis_signals: JSON array of signals [{time, type, description}]
        support_resistance: Optional S/R levels
        trend_lines: Optional trend line definitions
        interval: Chart timeframe
        
    Returns:
        JSON with chart file path
    """
    try:
        # Parse signals
        signals = json.loads(analysis_signals)
        
        # Convert to chart annotations
        annotations = []
        for signal in signals:
            annotations.append({
                "time": signal.get("time", int(datetime.now().timestamp())),
                "position": "aboveBar" if signal.get("type") == "buy" else "belowBar",
                "color": "#26a69a" if signal.get("type") == "buy" else "#ef5350",
                "shape": "arrowUp" if signal.get("type") == "buy" else "arrowDown",
                "text": signal.get("description", signal.get("type", "").upper()),
            })
        
        # Generate the chart with annotations
        return generate_tradingview_chart(
            symbol=symbol,
            interval=interval,
            indicators="volume,sma,bollinger",
            theme="dark",
            title=f"{symbol} AI Analysis",
            annotations=json.dumps(annotations),
        )
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to create annotated chart: {str(e)}",
        })


def generate_entry_analysis_chart(
    symbol: Annotated[str, "Trading pair symbol (e.g., 'BTCUSDT', 'ETHUSDT')"],
    entry_points: Annotated[str, """JSON array of entry point objects. Each entry should have:
        - type: 'long' or 'short' (required)
        - price: entry price level (required)
        - timestamp: Unix timestamp or ISO date string (optional, defaults to recent candle)
        - stop_loss: stop loss price (optional)
        - take_profit: take profit price or array of prices (optional)
        - reason: text explanation for the entry (optional)
        - confidence: 'high', 'medium', 'low' (optional)
        
        Example: [{"type": "long", "price": 98500, "stop_loss": 97000, "take_profit": [100000, 102000], "reason": "Breakout above resistance", "confidence": "high"}]
    """],
    interval: Annotated[str, "Chart interval: '5m', '15m', '1H', '4H', '1D'"] = "1H",
    support_levels: Annotated[Optional[str], "JSON array of support price levels, e.g., [95000, 92000]"] = None,
    resistance_levels: Annotated[Optional[str], "JSON array of resistance price levels, e.g., [100000, 105000]"] = None,
    indicators: Annotated[Optional[str], "Comma-separated list of built-in indicators: 'sma', 'ema', 'bollinger', 'rsi', 'macd', 'volume'. These show which indicators were used for the analysis."] = None,
    custom_indicators: Annotated[Optional[str], """JSON array of custom indicator data to overlay on the chart.
        Each custom indicator should have:
        - name: Display name for the legend (required)
        - data: Array of {time: unix_timestamp, value: number} points (required)
        - color: Hex color code (optional, default: '#00BCD4')
        - lineWidth: Line thickness 1-4 (optional, default: 2)
        - lineStyle: 0=solid, 1=dotted, 2=dashed (optional, default: 0)
        - priceScaleId: 'right' for main scale, or custom ID for separate scale (optional)
        
        Example: [{"name": "Custom RSI", "data": [{"time": 1701590400, "value": 65.5}, ...], "color": "#FF5722"}]
        
        This allows agents to create and display any custom indicator they calculate!
    """] = None,
    title: Annotated[Optional[str], "Chart title describing the analysis"] = None,
    show_risk_reward: Annotated[bool, "Whether to display risk/reward ratio for entries"] = True,
) -> str:
    """
    Generate a professional chart with entry/exit point annotations for trading analysis.
    
    This tool creates an interactive chart that visualizes:
    - Entry points with direction arrows (long/short)
    - Stop loss levels marked with red lines
    - Take profit targets with green lines
    - Support and resistance zones
    - Risk/reward ratio calculations
    - Entry reasoning annotations
    
    USE THIS TOOL when:
    - User asks for entry points or trade setups
    - Performing technical analysis with actionable signals
    - Creating trade idea visualizations
    - Showing where to enter/exit positions
    
    Args:
        symbol: Trading pair to analyze
        entry_points: JSON array of entry point definitions
        interval: Chart timeframe
        support_levels: Optional support price levels
        resistance_levels: Optional resistance price levels
        title: Chart title
        show_risk_reward: Display R:R calculations
        
    Returns:
        JSON with chart file path and entry analysis summary
    """
    try:
        _ensure_output_dir()
        
        # Parse entry points
        entries = json.loads(entry_points) if isinstance(entry_points, str) else entry_points
        supports = json.loads(support_levels) if support_levels else []
        resistances = json.loads(resistance_levels) if resistance_levels else []
        
        # Fetch real OHLCV data
        real_data = None
        candle_data = []
        try:
            from exchange_tools import get_ohlcv_data
            
            interval_map = {
                "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                "1H": "1h", "1h": "1h", "4H": "4h", "4h": "4h",
                "1D": "1d", "1d": "1d", "1W": "1w", "1w": "1w",
            }
            exchange_interval = interval_map.get(interval, "1h")
            
            result = json.loads(get_ohlcv_data(symbol, exchange_interval, limit=200))
            bars = result.get("data") or result.get("candles")
            if bars:
                for b in bars:
                    ts = b["timestamp"]
                    if isinstance(ts, str):
                        ts = int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())
                    else:
                        ts = int(ts) // 1000
                    candle_data.append({
                        "time": ts,
                        "open": float(b["open"]),
                        "high": float(b["high"]),
                        "low": float(b["low"]),
                        "close": float(b["close"]),
                        "volume": float(b.get("volume", 0)),
                    })
        except Exception as e:
            pass  # Will use placeholder data
        
        # Build annotations for markers
        markers = []
        price_lines = []
        entry_summary = []
        
        for i, entry in enumerate(entries):
            entry_type = entry.get("type", "long").lower()
            entry_price = float(entry.get("price", 0))
            stop_loss = entry.get("stop_loss")
            take_profit = entry.get("take_profit")
            reason = entry.get("reason", "")
            confidence = entry.get("confidence", "medium")
            
            # Get timestamp - find nearest candle or use most recent
            entry_time = entry.get("timestamp")
            if entry_time:
                if isinstance(entry_time, str):
                    entry_time = int(datetime.fromisoformat(entry_time.replace("Z", "+00:00")).timestamp())
            elif candle_data:
                # Find candle closest to entry price
                closest = min(candle_data[-50:], key=lambda c: abs(c["close"] - entry_price))
                entry_time = closest["time"]
            else:
                entry_time = int(datetime.now().timestamp())
            
            # Confidence colors
            conf_colors = {"high": "#00e676", "medium": "#ffc107", "low": "#ff9800"}
            
            # Entry marker
            marker_config = ANNOTATION_TYPES[f"entry_{entry_type}"]
            markers.append({
                "time": entry_time,
                "position": marker_config["position"],
                "color": conf_colors.get(confidence, marker_config["color"]),
                "shape": marker_config["shape"],
                "text": f"{entry_type.upper()} @ ${entry_price:,.2f}",
            })
            
            # Price lines for entry
            price_lines.append({
                "price": entry_price,
                "color": "#26a69a" if entry_type == "long" else "#ef5350",
                "lineWidth": 2,
                "lineStyle": 0,  # Solid
                "title": f"Entry {i+1}",
            })
            
            # Stop loss line
            if stop_loss:
                sl_price = float(stop_loss)
                price_lines.append({
                    "price": sl_price,
                    "color": "#ff5722",
                    "lineWidth": 1,
                    "lineStyle": 2,  # Dashed
                    "title": f"SL {i+1}",
                })
            
            # Take profit lines
            if take_profit:
                tps = take_profit if isinstance(take_profit, list) else [take_profit]
                for j, tp in enumerate(tps):
                    tp_price = float(tp)
                    price_lines.append({
                        "price": tp_price,
                        "color": "#4caf50",
                        "lineWidth": 1,
                        "lineStyle": 2,  # Dashed
                        "title": f"TP{j+1}",
                    })
            
            # Calculate risk/reward if both SL and TP provided
            rr_info = ""
            if stop_loss and take_profit:
                sl_price = float(stop_loss)
                tp_price = float(take_profit[0]) if isinstance(take_profit, list) else float(take_profit)
                if entry_type == "long":
                    risk = entry_price - sl_price
                    reward = tp_price - entry_price
                else:
                    risk = sl_price - entry_price
                    reward = entry_price - tp_price
                if risk > 0:
                    rr_ratio = reward / risk
                    rr_info = f"R:R = 1:{rr_ratio:.2f}"
            
            entry_summary.append({
                "type": entry_type,
                "price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "reason": reason,
                "confidence": confidence,
                "risk_reward": rr_info,
            })
        
        # Add support/resistance markers
        for s in supports:
            price_lines.append({
                "price": float(s),
                "color": "#2196f3",
                "lineWidth": 1,
                "lineStyle": 1,  # Dotted
                "title": "Support",
            })
        
        for r in resistances:
            price_lines.append({
                "price": float(r),
                "color": "#9c27b0",
                "lineWidth": 1,
                "lineStyle": 1,  # Dotted
                "title": "Resistance",
            })
        
        # Parse indicators
        indicator_list = [i.strip().lower() for i in indicators.split(",")] if indicators else []
        
        # Parse custom indicators
        custom_ind_list = []
        if custom_indicators:
            try:
                custom_ind_list = json.loads(custom_indicators) if isinstance(custom_indicators, str) else custom_indicators
            except json.JSONDecodeError:
                pass
        
        # Generate timestamp for unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chart_title = title or f"{symbol} Entry Analysis"
        filename = f"{symbol}_entry_analysis_{timestamp}.html"
        filepath = CHART_OUTPUT_DIR / filename
        
        # Build HTML with enhanced annotation rendering
        html_content = _generate_entry_analysis_html(
            symbol=symbol,
            interval=interval,
            title=chart_title,
            candle_data=candle_data,
            markers=markers,
            price_lines=price_lines,
            entry_summary=entry_summary,
            show_risk_reward=show_risk_reward,
            has_support=len(supports) > 0,
            has_resistance=len(resistances) > 0,
            indicators=indicator_list,
            custom_indicators=custom_ind_list,
        )
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        return json.dumps({
            "status": "success",
            "message": f"Entry analysis chart generated with {len(entries)} entry point(s)",
            "chart_file": str(filepath.absolute()),
            "filename": filename,
            "symbol": symbol,
            "interval": interval,
            "indicators": indicator_list,
            "entries": entry_summary,
            "support_levels": supports,
            "resistance_levels": resistances,
            "open_command": f"open {filepath.absolute()}",
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to generate entry analysis chart: {str(e)}",
        })


def _generate_entry_analysis_html(
    symbol: str,
    interval: str,
    title: str,
    candle_data: List[Dict],
    markers: List[Dict],
    price_lines: List[Dict],
    entry_summary: List[Dict],
    show_risk_reward: bool = True,
    has_support: bool = False,
    has_resistance: bool = False,
    indicators: List[str] = None,
    custom_indicators: List[Dict] = None,
) -> str:
    """Generate HTML for entry analysis chart with professional styling."""
    
    if indicators is None:
        indicators = []
    if custom_indicators is None:
        custom_indicators = []
    
    # Theme colors
    bg_color = "#1e222d"
    text_color = "#d1d4dc"
    grid_color = "#2a2e39"
    up_color = "#26a69a"
    down_color = "#ef5350"
    
    # Determine which legend items to show based on actual data
    has_long = any(e.get("type") == "long" for e in entry_summary)
    has_short = any(e.get("type") == "short" for e in entry_summary)
    has_stop_loss = any(e.get("stop_loss") for e in entry_summary)
    has_take_profit = any(e.get("take_profit") for e in entry_summary)
    
    # Build dynamic legend
    legend_items = []
    if has_long:
        legend_items.append(f'<div class="legend-item"><div class="legend-line" style="background: {up_color};"></div> Long Entry</div>')
    if has_short:
        legend_items.append(f'<div class="legend-item"><div class="legend-line" style="background: {down_color};"></div> Short Entry</div>')
    if has_stop_loss:
        legend_items.append('<div class="legend-item"><div class="legend-line" style="background: #ff5722; border-style: dashed;"></div> Stop Loss</div>')
    if has_take_profit:
        legend_items.append('<div class="legend-item"><div class="legend-line" style="background: #4caf50; border-style: dashed;"></div> Take Profit</div>')
    if has_support:
        legend_items.append('<div class="legend-item"><div class="legend-line" style="background: #2196f3; border-style: dotted;"></div> Support</div>')
    if has_resistance:
        legend_items.append('<div class="legend-item"><div class="legend-line" style="background: #9c27b0; border-style: dotted;"></div> Resistance</div>')
    
    # Add indicator legend items
    indicator_colors = {
        "sma": ("#2196F3", "SMA (20)"),
        "ema": ("#FF9800", "EMA (20)"),
        "bollinger": ("#9C27B0", "Bollinger Bands"),
        "volume": ("#607D8B", "Volume"),
        "rsi": ("#7b1fa2", "RSI (14)"),
        "macd": ("#00BCD4", "MACD"),
    }
    for ind in indicators:
        if ind in indicator_colors:
            color, label = indicator_colors[ind]
            legend_items.append(f'<div class="legend-item"><div class="legend-line" style="background: {color};"></div> {label}</div>')
    
    # Add custom indicator legend items
    for custom_ind in custom_indicators:
        ind_name = custom_ind.get("name", "Custom Indicator")
        ind_color = custom_ind.get("color", "#00BCD4")
        legend_items.append(f'<div class="legend-item"><div class="legend-line" style="background: {ind_color};"></div> {ind_name}</div>')
    
    legend_html = "\n".join(legend_items) if legend_items else '<p style="opacity: 0.5; font-size: 11px;">No annotations</p>'
    
    # Build entry summary panel with clickable cards
    summary_html = ""
    for i, entry in enumerate(entry_summary):
        entry_type = entry.get("type", "long")
        type_class = "long" if entry_type == "long" else "short"
        rr = entry.get("risk_reward", "")
        
        summary_html += f'''
        <div class="entry-card {type_class}" data-entry-index="{i}" onclick="toggleEntry({i})">
            <div class="entry-header">
                <span class="entry-type">{'🟢 LONG' if entry_type == 'long' else '🔴 SHORT'}</span>
                <span class="entry-confidence confidence-{entry.get('confidence', 'medium')}">{entry.get('confidence', 'medium').upper()}</span>
            </div>
            <div class="entry-price">Entry: ${entry.get('price', 0):,.2f}</div>
            <div class="entry-levels">
                <span class="sl">SL: ${float(entry.get('stop_loss', 0)):,.2f}</span>
                <span class="tp">TP: {entry.get('take_profit', 'N/A')}</span>
            </div>
            {f'<div class="risk-reward">{rr}</div>' if rr and show_risk_reward else ''}
            {f'<div class="entry-reason">{entry.get("reason", "")}</div>' if entry.get("reason") else ''}
        </div>
        '''
    
    # Add helper text for interactivity
    if entry_summary:
        summary_html = '<p style="font-size: 10px; opacity: 0.5; margin-bottom: 10px;">💡 Click entries to filter chart</p>' + summary_html
    
    # Generate chart data JS
    if candle_data:
        candles_js = json.dumps(candle_data)
        volumes_js = json.dumps([
            {"time": c["time"], "value": c.get("volume", 0), "color": up_color if c["close"] >= c["open"] else down_color}
            for c in candle_data
        ])
    else:
        candles_js = "[]"
        volumes_js = "[]"
    
    markers_js = json.dumps(markers)
    price_lines_js = json.dumps(price_lines)
    
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    {LIGHTWEIGHT_CHARTS_SCRIPT}
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: {bg_color};
            color: {text_color};
            padding: 20px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 0;
            border-bottom: 1px solid {grid_color};
            margin-bottom: 20px;
        }}
        .title {{
            font-size: 24px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .title-badge {{
            background: linear-gradient(135deg, {up_color}, {down_color});
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }}
        .info {{
            font-size: 14px;
            opacity: 0.7;
        }}
        .main-container {{
            display: grid;
            grid-template-columns: 1fr 300px;
            gap: 20px;
            height: calc(100vh - 150px);
        }}
        .chart-container {{
            background: {grid_color};
            border-radius: 8px;
            padding: 15px;
            min-height: 500px;
        }}
        #chart {{
            width: 100%;
            height: 100%;
        }}
        .sidebar {{
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}
        .panel {{
            background: {grid_color};
            border-radius: 8px;
            padding: 15px;
        }}
        .panel-title {{
            font-size: 14px;
            font-weight: 600;
            color: {up_color};
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .entry-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 6px;
            padding: 12px;
            margin-bottom: 10px;
            border-left: 3px solid;
            cursor: pointer;
            transition: all 0.2s ease;
            opacity: 1;
        }}
        .entry-card:hover {{
            background: rgba(255,255,255,0.1);
            transform: translateX(3px);
        }}
        .entry-card.dimmed {{
            opacity: 0.3;
        }}
        .entry-card.dimmed:hover {{
            opacity: 0.6;
        }}
        .entry-card.long {{ border-color: {up_color}; }}
        .entry-card.short {{ border-color: {down_color}; }}
        .entry-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        .entry-type {{
            font-weight: 600;
            font-size: 14px;
        }}
        .entry-confidence {{
            font-size: 10px;
            padding: 2px 8px;
            border-radius: 3px;
            font-weight: 600;
        }}
        .confidence-high {{ background: {up_color}; color: #000; }}
        .confidence-medium {{ background: #ffc107; color: #000; }}
        .confidence-low {{ background: #ff9800; color: #000; }}
        .entry-price {{
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 6px;
        }}
        .entry-levels {{
            display: flex;
            gap: 15px;
            font-size: 12px;
            opacity: 0.8;
        }}
        .sl {{ color: #ff5722; }}
        .tp {{ color: #4caf50; }}
        .risk-reward {{
            margin-top: 8px;
            padding: 4px 8px;
            background: rgba(38, 166, 154, 0.2);
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            color: {up_color};
            display: inline-block;
        }}
        .entry-reason {{
            margin-top: 8px;
            font-size: 11px;
            opacity: 0.7;
            font-style: italic;
        }}
        .legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 10px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 11px;
        }}
        .legend-color {{
            width: 12px;
            height: 3px;
            border-radius: 1px;
        }}
        .legend-marker {{
            font-size: 14px;
            font-weight: bold;
        }}
        .legend-line {{
            width: 20px;
            height: 2px;
            border-radius: 1px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <div class="title">
                📊 {title}
                <span class="title-badge">ENTRY ANALYSIS</span>
            </div>
            <div class="info">Interval: {interval} | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | MagenticOne AI</div>
        </div>
    </div>
    
    <div class="main-container">
        <div class="chart-container">
            <div id="chart"></div>
        </div>
        
        <div class="sidebar">
            <div class="panel">
                <div class="panel-title">🎯 Entry Points</div>
                {summary_html if summary_html else '<p style="opacity: 0.5; font-size: 12px;">No entry points defined</p>'}
            </div>
            
            <div class="panel">
                <div class="panel-title">📊 Chart Legend</div>
                <div class="legend">
                    {legend_html}
                </div>
            </div>
        </div>
    </div>

    <script>
        const container = document.getElementById('chart');
        
        const chart = LightweightCharts.createChart(container, {{
            autoSize: true,
            layout: {{
                background: {{ color: '{bg_color}' }},
                textColor: '{text_color}',
            }},
            grid: {{
                vertLines: {{ color: '{grid_color}' }},
                horzLines: {{ color: '{grid_color}' }},
            }},
            crosshair: {{
                mode: LightweightCharts.CrosshairMode.Normal,
            }},
            rightPriceScale: {{
                borderColor: '{grid_color}',
            }},
            timeScale: {{
                borderColor: '{grid_color}',
                timeVisible: true,
                secondsVisible: false,
            }},
        }});

        const candlestickSeries = chart.addCandlestickSeries({{
            upColor: '{up_color}',
            downColor: '{down_color}',
            borderDownColor: '{down_color}',
            borderUpColor: '{up_color}',
            wickDownColor: '{down_color}',
            wickUpColor: '{up_color}',
        }});

        // Volume series
        const volumeSeries = chart.addHistogramSeries({{ 
            priceFormat: {{ type: "volume" }}, 
            priceScaleId: "volume" 
        }});
        chart.priceScale("volume").applyOptions({{ scaleMargins: {{ top: 0.8, bottom: 0 }} }});

        // Entry point configurations from backend
        const entryPoints = {json.dumps(entry_summary)};
        
        // Load data
        let candleData = {candles_js};
        let volumeData = {volumes_js};
        
        // Generate placeholder if no real data
        if (candleData.length === 0) {{
            const now = Math.floor(Date.now() / 1000);
            // Use entry prices to create realistic price range
            const entryPrices = entryPoints.map(e => e.price).filter(p => p > 0);
            const avgPrice = entryPrices.length > 0 ? entryPrices.reduce((a, b) => a + b, 0) / entryPrices.length : 50000;
            const volatility = avgPrice * 0.02; // 2% volatility
            
            let price = avgPrice * 0.98; // Start slightly below average
            for (let i = 200; i >= 0; i--) {{
                const time = now - i * 3600;
                const open = price;
                const change = (Math.random() - 0.5) * volatility;
                const close = open + change;
                const high = Math.max(open, close) + Math.random() * (volatility * 0.3);
                const low = Math.min(open, close) - Math.random() * (volatility * 0.3);
                const volume = Math.random() * 1000000;
                candleData.push({{ time, open, high, low, close }});
                volumeData.push({{ time, value: volume, color: close >= open ? '{up_color}' : '{down_color}' }});
                price = close;
            }}
        }}
        
        candlestickSeries.setData(candleData);
        volumeSeries.setData(volumeData);

        // Technical Indicator Calculation Functions
        function calculateSMA(data, period) {{
            const sma = [];
            for (let i = period - 1; i < data.length; i++) {{
                let sum = 0;
                for (let j = 0; j < period; j++) {{
                    sum += data[i - j].close;
                }}
                sma.push({{ time: data[i].time, value: sum / period }});
            }}
            return sma;
        }}

        function calculateEMA(data, period) {{
            const ema = [];
            const multiplier = 2 / (period + 1);
            let emaPrev = data.slice(0, period).reduce((sum, d) => sum + d.close, 0) / period;
            
            for (let i = period - 1; i < data.length; i++) {{
                const emaValue = (data[i].close - emaPrev) * multiplier + emaPrev;
                ema.push({{ time: data[i].time, value: emaValue }});
                emaPrev = emaValue;
            }}
            return ema;
        }}

        function calculateBollingerBands(data, period, stdDev) {{
            const upper = [];
            const middle = [];
            const lower = [];
            
            for (let i = period - 1; i < data.length; i++) {{
                let sum = 0;
                for (let j = 0; j < period; j++) {{
                    sum += data[i - j].close;
                }}
                const sma = sum / period;
                
                let variance = 0;
                for (let j = 0; j < period; j++) {{
                    variance += Math.pow(data[i - j].close - sma, 2);
                }}
                const std = Math.sqrt(variance / period);
                
                upper.push({{ time: data[i].time, value: sma + stdDev * std }});
                middle.push({{ time: data[i].time, value: sma }});
                lower.push({{ time: data[i].time, value: sma - stdDev * std }});
            }}
            
            return {{ upper, middle, lower }};
        }}

        function calculateRSI(data, period) {{
            if (data.length < period + 1) return [];
            
            const rsi = [];
            let gains = [];
            let losses = [];
            
            for (let i = 1; i <= period; i++) {{
                const change = data[i].close - data[i - 1].close;
                gains.push(change > 0 ? change : 0);
                losses.push(change < 0 ? -change : 0);
            }}
            
            let avgGain = gains.reduce((a, b) => a + b, 0) / period;
            let avgLoss = losses.reduce((a, b) => a + b, 0) / period;
            
            for (let i = period; i < data.length; i++) {{
                const change = data[i].close - data[i - 1].close;
                const gain = change > 0 ? change : 0;
                const loss = change < 0 ? -change : 0;
                
                avgGain = (avgGain * (period - 1) + gain) / period;
                avgLoss = (avgLoss * (period - 1) + loss) / period;
                
                const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
                rsi.push({{ time: data[i].time, value: 100 - (100 / (1 + rs)) }});
            }}
            
            return rsi;
        }}

        // Add indicator overlays based on configuration
        const indicatorConfig = {json.dumps(indicators)};
        
        // SMA - Simple Moving Average (blue line)
        if (indicatorConfig.includes('sma')) {{
            const sma20Series = chart.addLineSeries({{ 
                color: '#2196F3', 
                lineWidth: 2,
                title: 'SMA 20'
            }});
            sma20Series.setData(calculateSMA(candleData, 20));
        }}
        
        // EMA - Exponential Moving Average (orange line)
        if (indicatorConfig.includes('ema')) {{
            const ema20Series = chart.addLineSeries({{ 
                color: '#FF9800', 
                lineWidth: 2,
                title: 'EMA 20'
            }});
            ema20Series.setData(calculateEMA(candleData, 20));
        }}
        
        // Bollinger Bands (purple)
        if (indicatorConfig.includes('bollinger')) {{
            const bb = calculateBollingerBands(candleData, 20, 2);
            
            const bbUpper = chart.addLineSeries({{ 
                color: '#9C27B0', 
                lineWidth: 1,
                lineStyle: 2,
            }});
            const bbMiddle = chart.addLineSeries({{ 
                color: '#9C27B0', 
                lineWidth: 1,
                lineStyle: 1,
            }});
            const bbLower = chart.addLineSeries({{ 
                color: '#9C27B0', 
                lineWidth: 1,
                lineStyle: 2,
            }});
            
            bbUpper.setData(bb.upper);
            bbMiddle.setData(bb.middle);
            bbLower.setData(bb.lower);
        }}

        // Render custom indicators (agent-created indicators with pre-calculated data)
        const customIndicators = {json.dumps(custom_indicators)};
        customIndicators.forEach((indicator, index) => {{
            const indName = indicator.name || `Custom ${{index + 1}}`;
            const indColor = indicator.color || '#00BCD4';
            const indWidth = indicator.lineWidth || 2;
            const indStyle = indicator.lineStyle || 0;
            const indData = indicator.data || [];
            const priceScaleId = indicator.priceScaleId || 'right';
            
            // Create line series for this custom indicator
            const customSeries = chart.addLineSeries({{
                color: indColor,
                lineWidth: indWidth,
                lineStyle: indStyle,
                title: indName,
                priceScaleId: priceScaleId,
                lastValueVisible: true,
                priceLineVisible: false,
            }});
            
            // If using a separate scale, configure it
            if (priceScaleId !== 'right') {{
                chart.priceScale(priceScaleId).applyOptions({{
                    scaleMargins: {{ top: 0.7, bottom: 0.05 }},
                }});
            }}
            
            // Set the indicator data
            if (indData.length > 0) {{
                customSeries.setData(indData);
            }}
        }});

        // Price lines configuration with entry index association
        const allPriceLines = {price_lines_js};
        const entryData = {json.dumps(entry_summary)};
        
        // Track which entries are selected (all visible by default)
        let selectedEntries = new Set();
        let isFilterMode = false;  // false = all visible, true = only selected visible
        
        // Map price lines to entry indices
        // Lines are created in order: Entry, SL, TPs for each entry, then Support, Resistance
        const entryLineMap = {{}};  // Maps line index to entry index
        let lineIdx = 0;
        entryData.forEach((entry, entryIdx) => {{
            // Entry line
            entryLineMap[lineIdx++] = {{ entryIndex: entryIdx, type: 'entry' }};
            // SL line if exists
            if (entry.stop_loss) {{
                entryLineMap[lineIdx++] = {{ entryIndex: entryIdx, type: 'sl' }};
            }}
            // TP lines if exist
            const tps = entry.take_profit;
            if (tps) {{
                const tpList = Array.isArray(tps) ? tps : [tps];
                tpList.forEach(() => {{
                    entryLineMap[lineIdx++] = {{ entryIndex: entryIdx, type: 'tp' }};
                }});
            }}
        }});
        // Remaining lines are support/resistance (always visible)
        const supportResistanceStartIdx = lineIdx;
        
        // Store created price line objects for visibility control
        let createdPriceLines = [];
        
        // Function to draw price lines based on selection
        function drawPriceLines() {{
            // Remove existing lines by recreating the series approach
            // Since LightweightCharts doesn't allow removing individual price lines,
            // we'll use visibility by setting price to NaN or using series
            
            // Clear existing price lines by storing references
            createdPriceLines.forEach(pl => {{
                try {{
                    candlestickSeries.removePriceLine(pl);
                }} catch(e) {{}}
            }});
            createdPriceLines = [];
            
            allPriceLines.forEach((line, idx) => {{
                const mapping = entryLineMap[idx];
                let shouldShow = true;
                
                if (mapping !== undefined) {{
                    // This is an entry-related line
                    if (isFilterMode) {{
                        shouldShow = selectedEntries.has(mapping.entryIndex);
                    }}
                }}
                // Support/Resistance lines always show
                
                if (shouldShow) {{
                    const pl = candlestickSeries.createPriceLine({{
                        price: line.price,
                        color: line.color,
                        lineWidth: line.lineWidth,
                        lineStyle: line.lineStyle,
                        axisLabelVisible: true,
                        title: line.title,
                    }});
                    createdPriceLines.push(pl);
                }}
            }});
        }}
        
        // Toggle entry visibility
        function toggleEntry(entryIndex) {{
            const card = document.querySelector(`[data-entry-index="${{entryIndex}}"]`);
            
            if (selectedEntries.has(entryIndex)) {{
                // Deselect this entry
                selectedEntries.delete(entryIndex);
                card.classList.add('dimmed');
            }} else {{
                // Select this entry
                selectedEntries.add(entryIndex);
                card.classList.remove('dimmed');
            }}
            
            // If no entries selected, show all (exit filter mode)
            if (selectedEntries.size === 0) {{
                isFilterMode = false;
                document.querySelectorAll('.entry-card').forEach(c => c.classList.remove('dimmed'));
            }} else {{
                isFilterMode = true;
                // Dim non-selected cards
                document.querySelectorAll('.entry-card').forEach(c => {{
                    const idx = parseInt(c.dataset.entryIndex);
                    if (!selectedEntries.has(idx)) {{
                        c.classList.add('dimmed');
                    }}
                }});
            }}
            
            // Redraw price lines
            drawPriceLines();
        }}
        
        // Make toggleEntry globally available
        window.toggleEntry = toggleEntry;
        
        // Initial draw
        drawPriceLines();

        // Fit content
        setTimeout(() => {{
            chart.timeScale().fitContent();
        }}, 100);
    </script>
</body>
</html>
'''
    
    return html_content


def generate_multi_timeframe_dashboard(
    symbol: Annotated[str, "Trading pair symbol"],
    timeframes: Annotated[str, "Comma-separated timeframes: '5m,1H,4H,1D'"] = "15m,1H,4H,1D",
) -> str:
    """
    Generate a multi-timeframe analysis dashboard.
    
    Creates an HTML dashboard showing the same symbol across
    multiple timeframes for comprehensive trend analysis.
    
    Args:
        symbol: Trading pair to analyze
        timeframes: Comma-separated list of intervals
        
    Returns:
        JSON with dashboard file path
    """
    try:
        _ensure_output_dir()
        
        tf_list = [tf.strip() for tf in timeframes.split(",")]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{symbol}_MTF_dashboard_{timestamp}.html"
        filepath = CHART_OUTPUT_DIR / filename
        
        # Generate chart iframes for each timeframe
        chart_panels = ""
        for i, tf in enumerate(tf_list):
            chart_panels += f'''
            <div class="chart-panel">
                <h3>{symbol} - {tf}</h3>
                <div id="chart-{i}" class="chart-frame"></div>
            </div>
            '''
        
        # Calculate grid layout
        cols = 2 if len(tf_list) <= 4 else 3
        
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{symbol} Multi-Timeframe Dashboard</title>
    {LIGHTWEIGHT_CHARTS_SCRIPT}
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1e222d;
            color: #d1d4dc;
            padding: 20px;
        }}
        .dashboard-header {{
            text-align: center;
            padding: 20px;
            border-bottom: 1px solid #2a2e39;
            margin-bottom: 20px;
        }}
        .dashboard-header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat({cols}, 1fr);
            gap: 20px;
        }}
        .chart-panel {{
            background: #2a2e39;
            border-radius: 8px;
            padding: 15px;
        }}
        .chart-panel h3 {{
            color: #26a69a;
            margin-bottom: 10px;
            font-size: 16px;
        }}
        .chart-frame {{
            width: 100%;
            height: 300px;
        }}
        .summary-panel {{
            margin-top: 20px;
            background: #2a2e39;
            border-radius: 8px;
            padding: 20px;
        }}
        .trend-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            border-radius: 4px;
            margin: 5px;
            font-weight: 600;
        }}
        .trend-up {{ background: #26a69a; }}
        .trend-down {{ background: #ef5350; }}
        .trend-neutral {{ background: #888; }}
    </style>
</head>
<body>
    <div class="dashboard-header">
        <h1>📊 {symbol} Multi-Timeframe Analysis</h1>
        <p>Timeframes: {', '.join(tf_list)} | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>
    
    <div class="dashboard-grid">
        {chart_panels}
    </div>
    
    <div class="summary-panel">
        <h3>🎯 Trend Summary</h3>
        <div id="trend-summary">
            {"".join([f'<span class="trend-indicator trend-neutral">{tf}: Analyzing...</span>' for tf in tf_list])}
        </div>
        <p style="margin-top: 15px; opacity: 0.7;">
            💡 <strong>Tip:</strong> Look for trend alignment across timeframes. 
            When all timeframes show the same direction, signals are stronger.
        </p>
    </div>

    <script>
        const symbol = '{symbol}';
        const timeframes = {json.dumps(tf_list)};
        
        // Create a chart for each timeframe
        timeframes.forEach((tf, index) => {{
            const container = document.getElementById(`chart-${{index}}`);
            const chart = LightweightCharts.createChart(container, {{
                width: container.clientWidth,
                height: 300,
                layout: {{
                    background: {{ color: '#1e222d' }},
                    textColor: '#d1d4dc',
                }},
                grid: {{
                    vertLines: {{ color: '#2a2e39' }},
                    horzLines: {{ color: '#2a2e39' }},
                }},
                timeScale: {{
                    timeVisible: true,
                }},
            }});
            
            const candlestickSeries = chart.addCandlestickSeries({{
                upColor: '#26a69a',
                downColor: '#ef5350',
                borderDownColor: '#ef5350',
                borderUpColor: '#26a69a',
                wickDownColor: '#ef5350',
                wickUpColor: '#26a69a',
            }});
            
            // Generate placeholder data
            const data = generateData(tf);
            candlestickSeries.setData(data);
            chart.timeScale().fitContent();
        }});
        
        function generateData(tf) {{
            const data = [];
            const now = Math.floor(Date.now() / 1000);
            let price = 50000 + Math.random() * 10000;
            const intervals = {{ '1m': 60, '5m': 300, '15m': 900, '1H': 3600, '4H': 14400, '1D': 86400 }};
            const interval = intervals[tf] || 3600;
            
            for (let i = 100; i >= 0; i--) {{
                const time = now - i * interval;
                const open = price;
                const change = (Math.random() - 0.5) * 500;
                const close = open + change;
                const high = Math.max(open, close) + Math.random() * 100;
                const low = Math.min(open, close) - Math.random() * 100;
                
                data.push({{ time, open, high, low, close }});
                price = close;
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
            "message": "Multi-timeframe dashboard generated",
            "dashboard_file": str(filepath.absolute()),
            "filename": filename,
            "symbol": symbol,
            "timeframes": tf_list,
            "open_command": f"open {filepath.absolute()}",
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to generate dashboard: {str(e)}",
        })


def generate_strategy_backtest_chart(
    symbol: Annotated[str, "Trading pair symbol"],
    strategy_name: Annotated[str, "Name of the strategy being backtested"],
    trades: Annotated[str, "JSON array of trades: [{entry_time, exit_time, entry_price, exit_price, type, profit}]"],
    equity_curve: Annotated[Optional[str], "JSON array of equity points: [{time, value}]"] = None,
    metrics: Annotated[Optional[str], "JSON object with strategy metrics: {win_rate, profit_factor, max_drawdown, etc}"] = None,
) -> str:
    """
    Generate a comprehensive strategy backtest visualization.
    
    Creates a professional chart showing:
    - All trade entries and exits on the price chart
    - Equity curve in a separate panel
    - Strategy performance metrics
    - Win/loss distribution
    
    This is the ULTIMATE tool for validating trading strategies
    with visual confirmation of every trade.
    
    Args:
        symbol: Trading pair
        strategy_name: Name of strategy
        trades: JSON array of trade data
        equity_curve: Optional equity curve data
        metrics: Optional strategy metrics
        
    Returns:
        JSON with chart file path
    """
    try:
        _ensure_output_dir()
        
        # Parse inputs
        trade_list = json.loads(trades)
        equity_data = json.loads(equity_curve) if equity_curve else []
        strategy_metrics = json.loads(metrics) if metrics else {}
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{symbol}_{strategy_name}_backtest_{timestamp}.html"
        filepath = CHART_OUTPUT_DIR / filename
        
        # Calculate trade stats
        winning_trades = [t for t in trade_list if t.get("profit", 0) > 0]
        losing_trades = [t for t in trade_list if t.get("profit", 0) <= 0]
        total_profit = sum(t.get("profit", 0) for t in trade_list)
        
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{strategy_name} Backtest - {symbol}</title>
    {LIGHTWEIGHT_CHARTS_SCRIPT}
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1e222d;
            color: #d1d4dc;
            padding: 20px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px;
            background: #2a2e39;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .header h1 {{ color: #26a69a; }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }}
        .metric-card {{
            background: #2a2e39;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 5px;
        }}
        .metric-value.positive {{ color: #26a69a; }}
        .metric-value.negative {{ color: #ef5350; }}
        .metric-label {{
            font-size: 12px;
            opacity: 0.7;
        }}
        .chart-container {{
            background: #2a2e39;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .chart-container h3 {{
            margin-bottom: 10px;
            color: #26a69a;
        }}
        #price-chart {{ height: 400px; }}
        #equity-chart {{ height: 200px; }}
        .trades-table {{
            background: #2a2e39;
            border-radius: 8px;
            padding: 15px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #3a3e49;
        }}
        th {{ color: #26a69a; }}
        .profit {{ color: #26a69a; }}
        .loss {{ color: #ef5350; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>🎯 {strategy_name}</h1>
            <p>{symbol} | Backtest Results | {len(trade_list)} Trades</p>
        </div>
        <div style="text-align: right;">
            <div class="metric-value {'positive' if total_profit > 0 else 'negative'}">
                {'+' if total_profit > 0 else ''}{total_profit:.2f}%
            </div>
            <div class="metric-label">Total Return</div>
        </div>
    </div>
    
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-value">{len(trade_list)}</div>
            <div class="metric-label">Total Trades</div>
        </div>
        <div class="metric-card">
            <div class="metric-value positive">{len(winning_trades)}</div>
            <div class="metric-label">Winning Trades</div>
        </div>
        <div class="metric-card">
            <div class="metric-value negative">{len(losing_trades)}</div>
            <div class="metric-label">Losing Trades</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{(len(winning_trades) / len(trade_list) * 100) if trade_list else 0:.1f}%</div>
            <div class="metric-label">Win Rate</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{strategy_metrics.get('profit_factor', 'N/A')}</div>
            <div class="metric-label">Profit Factor</div>
        </div>
    </div>
    
    <div class="chart-container">
        <h3>📊 Price Chart with Trade Signals</h3>
        <div id="price-chart"></div>
    </div>
    
    <div class="chart-container">
        <h3>📈 Equity Curve</h3>
        <div id="equity-chart"></div>
    </div>
    
    <div class="trades-table">
        <h3>📋 Trade History</h3>
        <table>
            <thead>
                <tr>
                    <th>Entry Time</th>
                    <th>Type</th>
                    <th>Entry Price</th>
                    <th>Exit Price</th>
                    <th>Profit</th>
                </tr>
            </thead>
            <tbody>
                {generate_trade_rows(trade_list)}
            </tbody>
        </table>
    </div>

    <script>
        const trades = {json.dumps(trade_list)};
        const equityData = {json.dumps(equity_data)};
        
        // Price chart
        const priceContainer = document.getElementById('price-chart');
        const priceChart = LightweightCharts.createChart(priceContainer, {{
            width: priceContainer.clientWidth,
            height: 400,
            layout: {{ background: {{ color: '#1e222d' }}, textColor: '#d1d4dc' }},
            grid: {{ vertLines: {{ color: '#2a2e39' }}, horzLines: {{ color: '#2a2e39' }} }},
        }});
        
        const candleSeries = priceChart.addCandlestickSeries({{
            upColor: '#26a69a',
            downColor: '#ef5350',
        }});
        
        // Generate placeholder price data
        const priceData = generatePriceData();
        candleSeries.setData(priceData);
        
        // Add trade markers
        const markers = trades.map(t => ({{
            time: t.entry_time || Math.floor(Date.now() / 1000),
            position: t.type === 'long' ? 'belowBar' : 'aboveBar',
            color: t.type === 'long' ? '#26a69a' : '#ef5350',
            shape: t.type === 'long' ? 'arrowUp' : 'arrowDown',
            text: t.type.toUpperCase(),
        }}));
        candleSeries.setMarkers(markers);
        
        // Equity chart
        const equityContainer = document.getElementById('equity-chart');
        const equityChart = LightweightCharts.createChart(equityContainer, {{
            width: equityContainer.clientWidth,
            height: 200,
            layout: {{ background: {{ color: '#1e222d' }}, textColor: '#d1d4dc' }},
            grid: {{ vertLines: {{ color: '#2a2e39' }}, horzLines: {{ color: '#2a2e39' }} }},
        }});
        
        const equitySeries = equityChart.addAreaSeries({{
            lineColor: '#26a69a',
            topColor: 'rgba(38, 166, 154, 0.4)',
            bottomColor: 'rgba(38, 166, 154, 0.0)',
        }});
        
        // Generate equity curve if not provided
        const equity = equityData.length > 0 ? equityData : generateEquityCurve(trades);
        equitySeries.setData(equity);
        
        priceChart.timeScale().fitContent();
        equityChart.timeScale().fitContent();
        
        function generatePriceData() {{
            const data = [];
            const now = Math.floor(Date.now() / 1000);
            let price = 50000;
            for (let i = 200; i >= 0; i--) {{
                const time = now - i * 3600;
                const open = price;
                price = price + (Math.random() - 0.5) * 500;
                const close = price;
                const high = Math.max(open, close) + Math.random() * 100;
                const low = Math.min(open, close) - Math.random() * 100;
                data.push({{ time, open, high, low, close }});
            }}
            return data;
        }}
        
        function generateEquityCurve(trades) {{
            const curve = [];
            const now = Math.floor(Date.now() / 1000);
            let equity = 10000;
            for (let i = 100; i >= 0; i--) {{
                equity = equity * (1 + (Math.random() - 0.48) * 0.02);
                curve.push({{ time: now - i * 3600, value: equity }});
            }}
            return curve;
        }}
    </script>
</body>
</html>
'''
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        return json.dumps({
            "status": "success",
            "message": "Strategy backtest chart generated",
            "chart_file": str(filepath.absolute()),
            "filename": filename,
            "symbol": symbol,
            "strategy": strategy_name,
            "total_trades": len(trade_list),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "total_profit": total_profit,
            "open_command": f"open {filepath.absolute()}",
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to generate backtest chart: {str(e)}",
        })


def generate_trade_rows(trades: List[Dict]) -> str:
    """Generate HTML table rows for trades."""
    rows = ""
    for t in trades[:20]:  # Limit to 20 for display
        profit_class = "profit" if t.get("profit", 0) > 0 else "loss"
        rows += f'''
        <tr>
            <td>{datetime.fromtimestamp(t.get("entry_time", 0)).strftime("%Y-%m-%d %H:%M") if t.get("entry_time") else "N/A"}</td>
            <td>{t.get("type", "N/A").upper()}</td>
            <td>${t.get("entry_price", 0):,.2f}</td>
            <td>${t.get("exit_price", 0):,.2f}</td>
            <td class="{profit_class}">{'+' if t.get("profit", 0) > 0 else ''}{t.get("profit", 0):.2f}%</td>
        </tr>
        '''
    return rows
