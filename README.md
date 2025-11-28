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
```bash
make setup    # Initial setup
make start    # Start services
make run      # Launch platform
```

### Local
```bash
make local-setup   # Create Python environment
ollama serve       # Start Ollama (separate terminal)
ollama pull gpt-oss:20b
make local-run     # Launch platform
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
make help       # Show all commands
make run        # Run (Docker)
make local-run  # Run (local)
make logs       # View logs
make shell      # Container shell
make clean      # Cleanup
make rebuild    # Rebuild containers
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
