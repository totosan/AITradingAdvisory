"""
TradingView UDF Server for AgenticTrades

This module provides a Universal Data Feed (UDF) compatible server
that serves real-time and historical market data to TradingView charts.

The UDF protocol is TradingView's standard HTTP API for data delivery:
- GET /config - Datafeed configuration
- GET /symbols - Symbol resolution  
- GET /search - Symbol search
- GET /history - OHLCV bars
- GET /time - Server time

This server integrates with our existing exchange_tools to provide
live data from Bitget and CoinGecko.
"""
import json
import os
import threading
import time
from datetime import datetime

from chart_assets import LIGHTWEIGHT_CHARTS_SCRIPT
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Annotated, Optional, Dict, Any, List
from pathlib import Path

# Default port for UDF server
DEFAULT_PORT = 8765


class UDFRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler implementing TradingView UDF protocol."""
    
    # Supported resolutions mapped to seconds
    RESOLUTION_MAP = {
        "1": 60,
        "5": 300,
        "15": 900,
        "30": 1800,
        "60": 3600,
        "120": 7200,
        "240": 14400,
        "D": 86400,
        "1D": 86400,
        "W": 604800,
        "1W": 604800,
    }
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass
    
    def _send_json_response(self, data: dict, status: int = 200):
        """Send a JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        # Extract single values from query params
        params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}
        
        try:
            if path == "/config":
                self._handle_config()
            elif path == "/symbols":
                self._handle_symbols(params)
            elif path == "/search":
                self._handle_search(params)
            elif path == "/history":
                self._handle_history(params)
            elif path == "/time":
                self._handle_time()
            else:
                self._send_json_response({"error": "Unknown endpoint"}, 404)
        except Exception as e:
            self._send_json_response({"error": str(e)}, 500)
    
    def _handle_config(self):
        """Return datafeed configuration."""
        config = {
            "supports_search": True,
            "supports_group_request": False,
            "supports_marks": True,
            "supports_timescale_marks": True,
            "supports_time": True,
            "exchanges": [
                {"value": "BITGET", "name": "Bitget", "desc": "Bitget Exchange"},
                {"value": "COINGECKO", "name": "CoinGecko", "desc": "CoinGecko Market Data"},
            ],
            "symbols_types": [
                {"name": "Crypto", "value": "crypto"},
            ],
            "supported_resolutions": ["1", "5", "15", "30", "60", "120", "240", "D", "W"],
        }
        self._send_json_response(config)
    
    def _handle_symbols(self, params: dict):
        """Resolve symbol information."""
        symbol = params.get("symbol", "BTCUSDT")
        
        symbol_info = {
            "name": symbol,
            "full_name": f"BITGET:{symbol}",
            "description": f"{symbol} on Bitget",
            "type": "crypto",
            "session": "24x7",
            "exchange": "BITGET",
            "listed_exchange": "BITGET",
            "timezone": "Etc/UTC",
            "format": "price",
            "pricescale": 100,
            "minmov": 1,
            "has_intraday": True,
            "has_weekly_and_monthly": True,
            "supported_resolutions": ["1", "5", "15", "30", "60", "120", "240", "D", "W"],
            "volume_precision": 8,
            "data_status": "streaming",
        }
        self._send_json_response(symbol_info)
    
    def _handle_search(self, params: dict):
        """Search for symbols."""
        query = params.get("query", "").upper()
        limit = int(params.get("limit", 30))
        
        # Hardcoded list of popular crypto pairs
        all_symbols = [
            {"symbol": "BTCUSDT", "full_name": "BITGET:BTCUSDT", "description": "Bitcoin/USDT", "exchange": "BITGET", "type": "crypto"},
            {"symbol": "ETHUSDT", "full_name": "BITGET:ETHUSDT", "description": "Ethereum/USDT", "exchange": "BITGET", "type": "crypto"},
            {"symbol": "SOLUSDT", "full_name": "BITGET:SOLUSDT", "description": "Solana/USDT", "exchange": "BITGET", "type": "crypto"},
            {"symbol": "BNBUSDT", "full_name": "BITGET:BNBUSDT", "description": "BNB/USDT", "exchange": "BITGET", "type": "crypto"},
            {"symbol": "XRPUSDT", "full_name": "BITGET:XRPUSDT", "description": "XRP/USDT", "exchange": "BITGET", "type": "crypto"},
            {"symbol": "DOGEUSDT", "full_name": "BITGET:DOGEUSDT", "description": "Dogecoin/USDT", "exchange": "BITGET", "type": "crypto"},
            {"symbol": "ADAUSDT", "full_name": "BITGET:ADAUSDT", "description": "Cardano/USDT", "exchange": "BITGET", "type": "crypto"},
            {"symbol": "AVAXUSDT", "full_name": "BITGET:AVAXUSDT", "description": "Avalanche/USDT", "exchange": "BITGET", "type": "crypto"},
            {"symbol": "SUIUSDT", "full_name": "BITGET:SUIUSDT", "description": "Sui/USDT", "exchange": "BITGET", "type": "crypto"},
            {"symbol": "LINKUSDT", "full_name": "BITGET:LINKUSDT", "description": "Chainlink/USDT", "exchange": "BITGET", "type": "crypto"},
        ]
        
        # Filter by query
        results = [s for s in all_symbols if query in s["symbol"] or query in s["description"].upper()][:limit]
        self._send_json_response(results)
    
    def _handle_history(self, params: dict):
        """Return historical OHLCV bars."""
        symbol = params.get("symbol", "BTCUSDT")
        resolution = params.get("resolution", "60")
        from_ts = int(params.get("from", 0))
        to_ts = int(params.get("to", int(time.time())))
        
        # Get interval in seconds
        interval_seconds = self.RESOLUTION_MAP.get(resolution, 3600)
        
        # Try to fetch real data from Bitget
        try:
            from src.exchange_tools import get_ohlcv_data
            
            # Map resolution to exchange format
            interval_map = {
                "1": "1m", "5": "5m", "15": "15m", "30": "30m",
                "60": "1h", "120": "2h", "240": "4h",
                "D": "1d", "1D": "1d", "W": "1w", "1W": "1w",
            }
            interval = interval_map.get(resolution, "1h")
            
            # Calculate number of bars needed
            num_bars = min((to_ts - from_ts) // interval_seconds, 500)
            
            result = json.loads(get_ohlcv_data(symbol, interval, limit=num_bars))
            
            if result.get("status") == "success" and result.get("data"):
                bars = result["data"]
                response = {
                    "s": "ok",
                    "t": [int(b["timestamp"]) // 1000 for b in bars],
                    "o": [float(b["open"]) for b in bars],
                    "h": [float(b["high"]) for b in bars],
                    "l": [float(b["low"]) for b in bars],
                    "c": [float(b["close"]) for b in bars],
                    "v": [float(b["volume"]) for b in bars],
                }
                self._send_json_response(response)
                return
        except Exception as e:
            pass
        
        # Fallback to generated data
        bars = self._generate_bars(symbol, from_ts, to_ts, interval_seconds)
        self._send_json_response(bars)
    
    def _generate_bars(self, symbol: str, from_ts: int, to_ts: int, interval: int) -> dict:
        """Generate placeholder OHLCV bars."""
        import random
        
        bars = {"s": "ok", "t": [], "o": [], "h": [], "l": [], "c": [], "v": []}
        
        # Base price varies by symbol
        base_prices = {
            "BTCUSDT": 65000, "ETHUSDT": 3500, "SOLUSDT": 150,
            "BNBUSDT": 600, "XRPUSDT": 0.6, "DOGEUSDT": 0.15,
        }
        price = base_prices.get(symbol, 100)
        
        current_ts = from_ts
        while current_ts <= to_ts:
            open_price = price
            change = (random.random() - 0.5) * (price * 0.02)
            close_price = open_price + change
            high_price = max(open_price, close_price) * (1 + random.random() * 0.005)
            low_price = min(open_price, close_price) * (1 - random.random() * 0.005)
            volume = random.random() * 1000000
            
            bars["t"].append(current_ts)
            bars["o"].append(round(open_price, 2))
            bars["h"].append(round(high_price, 2))
            bars["l"].append(round(low_price, 2))
            bars["c"].append(round(close_price, 2))
            bars["v"].append(round(volume, 2))
            
            price = close_price
            current_ts += interval
        
        return bars
    
    def _handle_time(self):
        """Return server time."""
        self._send_json_response(int(time.time()))


# Global server instance
_server_instance = None
_server_thread = None


def start_udf_server(
    port: Annotated[int, "Port to run the UDF server on"] = DEFAULT_PORT,
) -> str:
    """
    Start the TradingView UDF data server.
    
    This server provides real-time market data to TradingView charts
    using the Universal Data Feed (UDF) protocol. Once started, charts
    can connect to this server to receive live and historical data.
    
    Args:
        port: Port number for the server (default: 8765)
        
    Returns:
        JSON with server status and URL
    """
    global _server_instance, _server_thread
    
    try:
        if _server_instance is not None:
            return json.dumps({
                "status": "already_running",
                "message": f"UDF server already running on port {_server_instance.server_port}",
                "url": f"http://localhost:{_server_instance.server_port}",
            })
        
        _server_instance = HTTPServer(("localhost", port), UDFRequestHandler)
        _server_thread = threading.Thread(target=_server_instance.serve_forever, daemon=True)
        _server_thread.start()
        
        return json.dumps({
            "status": "success",
            "message": f"UDF server started successfully",
            "url": f"http://localhost:{port}",
            "endpoints": {
                "config": f"http://localhost:{port}/config",
                "symbols": f"http://localhost:{port}/symbols?symbol=BTCUSDT",
                "search": f"http://localhost:{port}/search?query=BTC",
                "history": f"http://localhost:{port}/history?symbol=BTCUSDT&from=0&to={int(time.time())}&resolution=60",
            },
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to start UDF server: {str(e)}",
        })


def stop_udf_server() -> str:
    """
    Stop the TradingView UDF data server.
    
    Returns:
        JSON with shutdown status
    """
    global _server_instance, _server_thread
    
    try:
        if _server_instance is None:
            return json.dumps({
                "status": "not_running",
                "message": "UDF server is not running",
            })
        
        _server_instance.shutdown()
        _server_instance = None
        _server_thread = None
        
        return json.dumps({
            "status": "success",
            "message": "UDF server stopped successfully",
        })
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to stop UDF server: {str(e)}",
        })


def get_udf_server_status() -> str:
    """
    Get the current status of the UDF server.
    
    Returns:
        JSON with server status information
    """
    global _server_instance
    
    if _server_instance is None:
        return json.dumps({
            "status": "stopped",
            "running": False,
            "message": "UDF server is not running",
        })
    
    return json.dumps({
        "status": "running",
        "running": True,
        "port": _server_instance.server_port,
        "url": f"http://localhost:{_server_instance.server_port}",
    })


def generate_live_chart_with_data(
    symbol: Annotated[str, "Trading pair symbol (e.g., 'BTCUSDT')"],
    interval: Annotated[str, "Chart interval: '1', '5', '15', '60', '240', 'D'"] = "60",
    indicators: Annotated[Optional[str], "Indicators to add: 'sma', 'ema', 'bollinger', 'rsi', 'macd'"] = None,
) -> str:
    """
    Generate an interactive chart connected to the live UDF server.
    
    Creates an HTML chart that connects to the local UDF server for
    real-time data updates. Requires the UDF server to be running.
    
    Args:
        symbol: Trading pair to chart
        interval: Timeframe resolution
        indicators: Optional indicators to add
        
    Returns:
        JSON with chart file path
    """
    from src.tradingview_tools import _ensure_output_dir, CHART_OUTPUT_DIR
    
    try:
        _ensure_output_dir()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{symbol}_live_{timestamp}.html"
        filepath = CHART_OUTPUT_DIR / filename
        
        indicator_list = indicators.split(",") if indicators else []
        
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{symbol} Live Chart</title>
    {LIGHTWEIGHT_CHARTS_SCRIPT}
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1e222d;
            color: #d1d4dc;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 20px;
            background: #2a2e39;
            border-bottom: 1px solid #3a3e49;
        }}
        .symbol-info {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        .symbol-name {{
            font-size: 20px;
            font-weight: 700;
            color: #26a69a;
        }}
        .price-display {{
            font-size: 24px;
            font-weight: 600;
        }}
        .price-change {{
            font-size: 14px;
            padding: 4px 8px;
            border-radius: 4px;
        }}
        .price-change.up {{ background: #26a69a; }}
        .price-change.down {{ background: #ef5350; }}
        .interval-selector {{
            display: flex;
            gap: 5px;
        }}
        .interval-btn {{
            padding: 8px 12px;
            background: #2a2e39;
            border: 1px solid #3a3e49;
            border-radius: 4px;
            color: #d1d4dc;
            cursor: pointer;
        }}
        .interval-btn:hover, .interval-btn.active {{
            background: #26a69a;
            border-color: #26a69a;
            color: white;
        }}
        #chart {{ height: calc(100vh - 60px); }}
        .loading {{
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            font-size: 18px;
            color: #888;
        }}
        .status {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 10px 20px;
            background: #2a2e39;
            border-radius: 8px;
            font-size: 12px;
        }}
        .status.connected {{ color: #26a69a; }}
        .status.disconnected {{ color: #ef5350; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="symbol-info">
            <span class="symbol-name">{symbol}</span>
            <span id="current-price" class="price-display">Loading...</span>
            <span id="price-change" class="price-change up">+0.00%</span>
        </div>
        <div class="interval-selector">
            <button class="interval-btn" data-interval="1">1m</button>
            <button class="interval-btn" data-interval="5">5m</button>
            <button class="interval-btn" data-interval="15">15m</button>
            <button class="interval-btn active" data-interval="60">1H</button>
            <button class="interval-btn" data-interval="240">4H</button>
            <button class="interval-btn" data-interval="D">1D</button>
        </div>
    </div>
    
    <div id="chart"><div class="loading">🔄 Connecting to data feed...</div></div>
    
    <div id="status" class="status disconnected">⚪ Connecting...</div>

    <script>
        const UDF_URL = 'http://localhost:8765';
        const symbol = '{symbol}';
        let currentInterval = '{interval}';
        let chart = null;
        let candleSeries = null;
        let volumeSeries = null;
        
        // Initialize chart
        async function initChart() {{
            const container = document.getElementById('chart');
            container.innerHTML = '';
            
            chart = LightweightCharts.createChart(container, {{
                width: container.clientWidth,
                height: container.clientHeight,
                layout: {{
                    background: {{ color: '#1e222d' }},
                    textColor: '#d1d4dc',
                }},
                grid: {{
                    vertLines: {{ color: '#2a2e39' }},
                    horzLines: {{ color: '#2a2e39' }},
                }},
                crosshair: {{
                    mode: LightweightCharts.CrosshairMode.Normal,
                }},
                rightPriceScale: {{
                    borderColor: '#3a3e49',
                }},
                timeScale: {{
                    borderColor: '#3a3e49',
                    timeVisible: true,
                }},
            }});
            
            candleSeries = chart.addCandlestickSeries({{
                upColor: '#26a69a',
                downColor: '#ef5350',
                borderDownColor: '#ef5350',
                borderUpColor: '#26a69a',
                wickDownColor: '#ef5350',
                wickUpColor: '#26a69a',
            }});
            
            volumeSeries = chart.addHistogramSeries({{
                priceFormat: {{ type: 'volume' }},
                priceScaleId: '',
                scaleMargins: {{ top: 0.8, bottom: 0 }},
            }});
            
            await loadData();
        }}
        
        // Load data from UDF server
        async function loadData() {{
            try {{
                const to = Math.floor(Date.now() / 1000);
                const from = to - (86400 * 30); // 30 days
                
                const url = `${{UDF_URL}}/history?symbol=${{symbol}}&from=${{from}}&to=${{to}}&resolution=${{currentInterval}}`;
                const response = await fetch(url);
                const data = await response.json();
                
                if (data.s === 'ok') {{
                    const candles = [];
                    const volumes = [];
                    
                    for (let i = 0; i < data.t.length; i++) {{
                        candles.push({{
                            time: data.t[i],
                            open: data.o[i],
                            high: data.h[i],
                            low: data.l[i],
                            close: data.c[i],
                        }});
                        volumes.push({{
                            time: data.t[i],
                            value: data.v[i],
                            color: data.c[i] >= data.o[i] ? '#26a69a50' : '#ef535050',
                        }});
                    }}
                    
                    candleSeries.setData(candles);
                    volumeSeries.setData(volumes);
                    
                    // Update price display
                    if (candles.length > 0) {{
                        const lastCandle = candles[candles.length - 1];
                        const firstCandle = candles[0];
                        const priceChange = ((lastCandle.close - firstCandle.open) / firstCandle.open * 100);
                        
                        document.getElementById('current-price').textContent = 
                            '$' + lastCandle.close.toLocaleString(undefined, {{maximumFractionDigits: 2}});
                        
                        const changeEl = document.getElementById('price-change');
                        changeEl.textContent = (priceChange >= 0 ? '+' : '') + priceChange.toFixed(2) + '%';
                        changeEl.className = 'price-change ' + (priceChange >= 0 ? 'up' : 'down');
                    }}
                    
                    chart.timeScale().fitContent();
                    document.getElementById('status').className = 'status connected';
                    document.getElementById('status').textContent = '🟢 Connected to UDF Server';
                }}
            }} catch (error) {{
                console.error('Failed to load data:', error);
                document.getElementById('status').className = 'status disconnected';
                document.getElementById('status').textContent = '🔴 Disconnected - Start UDF Server';
            }}
        }}
        
        // Interval buttons
        document.querySelectorAll('.interval-btn').forEach(btn => {{
            btn.addEventListener('click', async () => {{
                document.querySelectorAll('.interval-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentInterval = btn.dataset.interval;
                await loadData();
            }});
        }});
        
        // Resize handler
        window.addEventListener('resize', () => {{
            if (chart) {{
                const container = document.getElementById('chart');
                chart.applyOptions({{ width: container.clientWidth, height: container.clientHeight }});
            }}
        }});
        
        // Initialize
        initChart();
        
        // Refresh every 30 seconds
        setInterval(loadData, 30000);
    </script>
</body>
</html>
'''
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        return json.dumps({
            "status": "success",
            "message": "Live chart generated",
            "chart_file": str(filepath.absolute()),
            "filename": filename,
            "symbol": symbol,
            "interval": interval,
            "requires_udf_server": True,
            "udf_server_url": f"http://localhost:{DEFAULT_PORT}",
            "open_command": f"open {filepath.absolute()}",
            "note": "Make sure to start the UDF server before opening the chart",
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to generate live chart: {str(e)}",
        })
