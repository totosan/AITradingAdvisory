# 🪙 Crypto Analysis Platform

**A multi-agent cryptocurrency analysis system powered by MagenticOne.**

Real-time market data, technical analysis, TradingView-style charts, and AI-powered trading insights.

---

## 🎯 Features

### 🤖 Multi-Agent Team
| Agent | Role |
|-------|------|
| **📊 Market Analyst** | Prices, trends, market data, custom indicator ideas |
| **📈 Technical Analyst** | Charts, indicators, signals, strategy design |
| **📉 Charting Agent** | TradingView charts, multi-timeframe dashboards |
| **👨‍💻 Analysis Coder** | Custom indicators, backtesting, code execution |
| **📝 Report Writer** | Professional Markdown reports |
| **🖥️ Executor** | Code execution sandbox |

### 📊 Technical Analysis
- **Indicators**: RSI, MACD, Bollinger Bands, SMA, EMA
- **Custom Indicators**: Create, save, and reuse your own indicators
- **Signal Detection**: Overbought/oversold, trend changes, divergences

### 📉 Professional Charting
- **TradingView-style** interactive HTML charts
- **Multi-timeframe dashboards** (1H, 4H, 1D views)
- **AI-annotated charts** with buy/sell markers
- **Backtest visualizations** with equity curves

### 🚨 Smart Alerts
- **AI-powered scanning** across multiple symbols
- **Confluence scoring** from multiple indicators
- **Trade ideas** with entry/stop/target levels

### 💹 Data Sources
- **🔶 Bitget Exchange** - Real-time spot & futures, order books, OHLCV
- **🦎 CoinGecko** - 10,000+ coins, historical data, market info

---

## 🚀 Quick Start

### Docker (Recommended)

From your host terminal:

```bash
make dev    # Start backend + frontend with Docker
```

**What you'll see:**
```
🔧 Starting development mode (Docker)...
 ✔ Container magentic-backend-dev    Started
 ✔ Container magentic-frontend-dev   Started
magentic-backend-dev   | 🚀 Starting MagenticOne API
magentic-backend-dev   | INFO:     Uvicorn running on http://0.0.0.0:8500
```

**Access:**
- 🌐 **Frontend**: http://localhost:5173
- 📚 **API Docs**: http://localhost:8500/docs

Press `Ctrl+C` to stop.

### Other Commands

```bash
make dev          # Docker development mode
make dev-local    # Local mode (no Docker, hot reload)
make prod         # Production mode
make stop         # Stop all services
```

### Configuration

Create `.env` in project root:

```bash
# Azure OpenAI
LLM_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Or Ollama (local LLM)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2:latest
```

---

## 💬 Usage

Start the platform and ask questions:

```
> Analyze BTCUSDT with technical indicators
> Generate a multi-timeframe dashboard for ETH
> Create a TradingView chart for SUI with RSI and volume
> Compare Solana vs Avalanche performance
> Scan top coins for trading opportunities
```

### Conversation Mode
The platform remembers context - ask follow-up questions:
```
> Analyze Bitcoin
> Now show me a chart
> What about Ethereum?
```

### Commands
- `/clear` - Reset conversation history
- `/history` - Show previous turns
- `/single` - Toggle one-shot mode
- `exit` - Quit

---

## 📁 Project Structure

```
MagenticOne/
├── src/
│   ├── main.py                 # Entry point & agent definitions
│   ├── config.py               # Configuration
│   ├── ollama_client.py        # LLM client with function calling
│   ├── crypto_tools.py         # CoinGecko data & indicators
│   ├── crypto_charts.py        # Plotly chart generation
│   ├── exchange_tools.py       # Bitget exchange integration
│   ├── tradingview_tools.py    # TradingView-style charts
│   ├── tradingview_udf_server.py  # Live data server
│   ├── smart_alerts.py         # AI alert dashboard
│   ├── report_tools.py         # Markdown report generation
│   ├── indicator_registry.py   # Persistent custom indicators
│   └── exchange_providers/     # Exchange abstraction layer
├── outputs/
│   ├── charts/                 # Generated HTML charts
│   ├── dashboards/             # Multi-timeframe views
│   ├── alerts/                 # Alert dashboards
│   └── code_execution/         # Executed scripts
├── data/
│   └── indicators/             # Saved custom indicators
├── config/
│   └── .env.example            # Environment template
├── docker-compose.yml
├── Dockerfile
├── Makefile
└── pyproject.toml
```

---

## ⚙️ Configuration

### Environment Variables
```bash
# LLM Provider (azure or ollama)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gpt-oss:20b

# Exchange (optional)
BITGET_API_KEY=your-key
BITGET_API_SECRET=your-secret
BITGET_PASSPHRASE=your-passphrase
```

### Compatible Models
- `gpt-oss:20b` - Recommended
- `llama3.2` - Good alternative
- `mistral`, `mixtral` - Also supported

---

## 🛠️ Commands

```bash
make help         # Show all commands
make dev          # Development mode (Docker)
make dev-local    # Development mode (local, hot reload)
make dev-backend  # Backend only (local)
make dev-frontend # Frontend only (local)
make prod         # Production mode
make stop         # Stop all services
make logs         # View logs
make status       # Check container status
make clean        # Cleanup
```

---

## 📈 Symbol Formats

| Source | Format | Example |
|--------|--------|---------|
| CoinGecko | lowercase ID | `bitcoin`, `ethereum`, `sui` |
| Bitget | trading pair | `BTCUSDT`, `ETHUSDT`, `SUIUSDT` |

---

## ⚠️ Disclaimer

**For educational and research purposes only.**

- This is NOT financial advice
- Cryptocurrency trading carries substantial risk
- Always do your own research (DYOR)
- Past performance ≠ future results

---

## 📝 Built With

- [MagenticOne/AutoGen](https://github.com/microsoft/autogen) - Multi-agent framework
- [Ollama](https://ollama.ai) - Local LLM runtime
- [Lightweight Charts](https://www.tradingview.com/lightweight-charts/) - TradingView charting
- [CoinGecko API](https://www.coingecko.com) - Market data
- [Bitget API](https://www.bitget.com) - Exchange data
