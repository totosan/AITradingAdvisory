"""
Crypto Analysis Architecture Diagram

This module demonstrates the flow of the crypto analysis agent system.
"""

CRYPTO_AGENT_ARCHITECTURE = """
┌─────────────────────────────────────────────────────────────────┐
│                    USER INTERACTION                             │
│  • Interactive CLI Commands                                     │
│  • Direct Task Descriptions                                     │
│  • Makefile Commands (make crypto / make crypto-interactive)   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              🎯 MAGENTICONE ORCHESTRATOR                        │
│  • Coordinates crypto analysis team                             │
│  • Plans multi-step analysis tasks                              │
│  • Routes to appropriate specialist agents                      │
│  • Maintains analysis progress                                  │
└─────┬──────────────┬──────────────┬────────────┬───────────────┘
      │              │              │            │
      │              │              │            │
┌─────▼────┐   ┌────▼─────┐   ┌───▼──────┐  ┌──▼────────┐
│    📊    │   │    📈    │   │   👨‍💻    │  │    🖥️     │
│  Market  │   │Technical │   │ Analysis │  │ Executor  │
│ Analyst  │   │ Analyst  │   │  Coder   │  │           │
└─────┬────┘   └────┬─────┘   └───┬──────┘  └──┬────────┘
      │              │              │            │
      │              │              │            │
┌─────▼──────────────▼──────────────▼────────────▼───────────────┐
│                    CRYPTO ANALYSIS TOOLS                        │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Data Fetching (crypto_tools.py)                       │   │
│  │  • get_crypto_price() - Real-time prices               │   │
│  │  • get_historical_data() - Historical OHLC data        │   │
│  │  • get_market_info() - Market cap, volume, rankings    │   │
│  └────────────────────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Technical Indicators (crypto_tools.py)                │   │
│  │  • calculate_rsi() - Overbought/oversold               │   │
│  │  • calculate_macd() - Momentum and trend               │   │
│  │  • calculate_bollinger_bands() - Volatility            │   │
│  │  • calculate_sma/ema() - Moving averages               │   │
│  │  • analyze_technical_indicators() - Full analysis      │   │
│  └────────────────────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Chart Generation (crypto_charts.py)                   │   │
│  │  • create_crypto_chart() - Candlestick charts          │   │
│  │  • Interactive HTML with Plotly                        │   │
│  │  • Multiple indicator overlays                         │   │
│  │  • Customizable timeframes                             │   │
│  └────────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                   EXTERNAL DATA SOURCES                         │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  CoinGecko API (Free Tier)                             │   │
│  │  • 10,000+ cryptocurrencies                            │   │
│  │  • Real-time prices & market data                      │   │
│  │  • Historical OHLC data (up to 365 days)               │   │
│  │  • No API key required                                 │   │
│  └────────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      OUTPUT RESULTS                             │
│  • Interactive HTML Charts (outputs/)                           │
│  • Technical Analysis Reports                                   │
│  • Trading Signals & Recommendations                            │
│  • Multi-coin Comparisons                                       │
│  • Market Sentiment Analysis                                    │
└─────────────────────────────────────────────────────────────────┘


AGENT SPECIALIZATIONS:
═══════════════════════

📊 Crypto Market Analyst
─────────────────────────
• Fetches current prices and market data
• Tracks 24h/7d/30d price changes
• Analyzes market cap and volume
• Compares multiple cryptocurrencies
• Identifies market trends

Tools: get_crypto_price, get_historical_data, get_market_info

📈 Technical Analyst
────────────────────
• Calculates RSI, MACD, Bollinger Bands
• Generates candlestick charts
• Detects overbought/oversold conditions
• Identifies bullish/bearish signals
• Provides entry/exit recommendations

Tools: create_crypto_chart, analyze_technical_indicators

👨‍💻 Analysis Coder
─────────────────
• Creates custom analysis scripts
• Processes multi-coin comparisons
• Generates comprehensive reports
• Handles complex calculations
• Builds visualizations

Tools: All crypto tools + Python scripting

🖥️ Code Executor
────────────────
• Runs analysis scripts safely
• Executes chart generation
• Saves outputs to disk
• Handles errors gracefully
• Manages file system operations


TECHNICAL INDICATORS:
═════════════════════

RSI (Relative Strength Index)
──────────────────────────────
Values: 0-100
• < 30: OVERSOLD (potential buy)
• > 70: OVERBOUGHT (potential sell)
• 30-70: Normal range

MACD (Moving Average Convergence Divergence)
─────────────────────────────────────────────
Components: MACD line, Signal line, Histogram
• Positive histogram: Bullish
• Negative histogram: Bearish
• Crossovers: Trend changes

Bollinger Bands
───────────────
Components: Upper, Middle (SMA 20), Lower
• Price near upper: Potentially overbought
• Price near lower: Potentially oversold
• Band squeeze: Breakout imminent

Moving Averages
───────────────
SMA (Simple) & EMA (Exponential)
• Price > MA: Bullish trend
• Price < MA: Bearish trend
• SMA20 > SMA50: Golden cross
• SMA20 < SMA50: Death cross


EXAMPLE WORKFLOWS:
══════════════════

Single Coin Analysis
────────────────────
User: "Analyze Bitcoin"
  ↓
Orchestrator: Plans analysis steps
  ↓
Market Analyst: Fetches current price & market data
  ↓
Technical Analyst: Calculates indicators & generates chart
  ↓
Coder: Creates analysis script if needed
  ↓
Executor: Runs code, generates visualizations
  ↓
Result: Complete analysis with chart & signals

Multi-Coin Comparison
─────────────────────
User: "Compare Ethereum vs Solana"
  ↓
Orchestrator: Plans comparative analysis
  ↓
Market Analyst: Fetches data for both coins
  ↓
Technical Analyst: Calculates indicators for both
  ↓
Coder: Creates comparison script
  ↓
Executor: Generates side-by-side analysis
  ↓
Result: Comparative report with recommendations

Chart Generation
────────────────
User: "Chart Cardano 30 days with RSI and MACD"
  ↓
Technical Analyst: Fetches 30 days of OHLC data
  ↓
Technical Analyst: Calculates RSI & MACD
  ↓
Technical Analyst: Generates interactive chart
  ↓
Executor: Saves chart as HTML
  ↓
Result: Interactive chart in outputs/ directory
"""


def print_architecture():
    """Print the crypto analysis architecture diagram."""
    print(CRYPTO_AGENT_ARCHITECTURE)


if __name__ == "__main__":
    print_architecture()
