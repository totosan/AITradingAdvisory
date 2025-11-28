# 🪙 Crypto Analysis Platform

**A specialized multi-agent cryptocurrency analysis system powered by MagenticOne.**

This platform combines AI-driven multi-agent coordination with real-time cryptocurrency data, technical analysis indicators, and professional charting capabilities to provide comprehensive market insights.

---

## 🎯 Overview

The Crypto Analysis Platform leverages MagenticOne's multi-agent architecture to create a specialized team of AI agents that work together to analyze cryptocurrency markets. Each agent has specific expertise and tools to fetch data, perform calculations, generate charts, and provide actionable insights.

### 🤖 Multi-Agent System

- **Crypto Market Analyst** - Fetches real-time prices, market trends, and fundamentals
- **Technical Analyst** - Calculates indicators, identifies patterns, generates trading signals
- **Analysis Coder** - Creates custom Python scripts for multi-coin comparisons
- **Code Executor** - Executes analysis code and generates visualizations

### 📊 Key Features

- ✅ **Real-time Price Monitoring** - Track 10,000+ cryptocurrencies via CoinGecko API
- ✅ **Technical Indicators** - RSI, MACD, Bollinger Bands, SMA, EMA
- ✅ **Professional Charts** - Interactive candlestick charts with Plotly
- ✅ **Trading Signals** - Overbought/oversold detection, trend analysis
- ✅ **Market Analysis** - Compare multiple coins, identify opportunities
- ✅ **Function Calling** - Native tool integration with Ollama models

### 📈 Technical Indicators

| Indicator | Purpose | Signals |
|-----------|---------|---------|
| **RSI (14)** | Momentum oscillator | < 30 = Oversold, > 70 = Overbought |
| **MACD (12,26,9)** | Trend & momentum | Crossover = Trend change |
| **Bollinger Bands (20,2)** | Volatility measure | Price at bands = Potential reversal |
| **SMA/EMA** | Trend direction | Price vs MA = Bullish/Bearish |

---

## 🚀 Installation

### Prerequisites

- **Python 3.10+** - Required for async operations
- **Ollama** - Local LLM runtime ([Installation guide](https://ollama.ai))
- **Docker** (optional) - For containerized deployment
- **Internet connection** - For CoinGecko API access

### Quick Setup

#### Option 1: Docker (Recommended)

```bash
# 1. Complete setup (installs dependencies, configures Docker)
make setup

# 2. Start services
make start

# 3. Run crypto analysis
make run
```

#### Option 2: Local Installation

```bash
# 1. Set up Python environment
make local-setup

# 2. Start Ollama (in separate terminal)
ollama serve

# 3. Pull a compatible model
ollama pull gpt-oss:20b
# OR
ollama pull llama3.2

# 4. Run crypto analysis
make local-run
```

### Verify Installation

```bash
# Test the platform
python verify_platform.py

# Quick demo
python demo.py
```

---

## 💻 Getting Started

### Interactive Mode (Recommended)

```bash
# With Docker
make run

# Locally
source .venv/bin/activate
python src/main.py
```

**Example Queries:**
```
> Analyze bitcoin with technical indicators
> What's the current price of ethereum and solana?
> Compare cardano vs polkadot performance
> Generate a 30-day chart for bitcoin with RSI and MACD
> Which of the top 5 coins shows the strongest buy signal?
```

### Advanced Analysis Mode

```bash
# Docker
make crypto-interactive

# Local
source .venv/bin/activate
python examples/crypto_analysis.py --mode interactive
```

### Direct Task Execution

```bash
# Pass a specific query as an argument
python src/main.py "Analyze Bitcoin with full technical analysis"
```

### Advanced Analysis Mode

```bash
# Docker
make crypto-interactive

# Local
source .venv/bin/activate
python examples/crypto_analysis.py --mode interactive
```

### Direct Task Execution

```bash
# Pass a specific query as an argument
python src/main.py "Analyze Bitcoin with full technical analysis"
```

---

## 📊 Usage Examples

### 1. Single Coin Analysis

**Query:**
```
Analyze Bitcoin with:
1. Current price and market data
2. RSI, MACD, and Bollinger Bands
3. Generate 30-day candlestick chart
4. Provide trading signals and recommendations
```

**Output:**
- Current price, market cap, 24h volume
- Technical indicator values and interpretations
- Interactive HTML chart saved to `outputs/bitcoin_chart_*.html`
- Trading recommendations (buy/sell/hold)

### 2. Multi-Coin Comparison

**Query:**
```
Compare Ethereum vs Solana:
- Price performance over 24h, 7d, 30d
- Market cap and volume comparison  
- Technical indicator analysis
- Which shows stronger buy signals?
```

**Output:**
- Side-by-side performance metrics
- Relative strength comparison
- Technical indicator comparison table
- Recommendation with rationale

### 3. Market Overview

**Query:**
```
Analyze the top 3 cryptocurrencies and identify
which has the best technical setup right now
```

**Output:**
- Bitcoin, Ethereum, BNB analysis
- Technical ranking by indicator confluence
- Best opportunity identification
- Risk/reward assessment

---

## 🪙 Supported Cryptocurrencies

The platform supports 10,000+ cryptocurrencies through the CoinGecko API. Use the exact CoinGecko ID for best results.

**Popular Examples:**
```
bitcoin, ethereum, solana, cardano, polkadot, avalanche-2,
ripple, dogecoin, chainlink, polygon, uniswap, shiba-inu,
litecoin, bitcoin-cash, stellar, cosmos, algorand, tezos
```

💡 **Tip:** Use full names (e.g., `bitcoin` not `BTC`) and check [CoinGecko](https://www.coingecko.com) for correct IDs.

---

## 📁 Project Structure

```
MagenticOne/
├── src/
│   ├── main.py              # Main entry point for crypto analysis
│   ├── config.py            # Configuration management
│   ├── ollama_client.py     # Ollama LLM integration
│   ├── crypto_tools.py      # Data fetching & technical indicators
│   ├── crypto_charts.py     # Chart generation with Plotly
│   └── crypto_architecture.py  # Multi-agent system architecture
├── examples/
│   └── crypto_analysis.py   # Advanced crypto analysis examples
├── outputs/                 # Generated charts and analysis reports
│   ├── *.html              # Interactive candlestick charts
│   └── task_output_*.txt   # Analysis logs
├── docker-compose.yml       # Docker services configuration
├── Dockerfile              # Container definition
├── Makefile                # Convenience commands
├── pyproject.toml          # Python dependencies
└── README.md               # This file
```

---

## 🔧 Configuration

### Model Configuration

Edit `src/config.py` to change the Ollama model:

```python
@dataclass
class OllamaConfig:
    base_url: str = "http://localhost:11434"
    model: str = "gpt-oss:20b"  # Change to your preferred model
    temperature: float = 0.7
```

**Compatible Models:**
- `gpt-oss:20b` - Recommended for function calling
- `llama3.2` - Good balance of speed and quality  
- `deepseek-r1:1.5b` - Fast and efficient
- `mistral` - Strong reasoning capabilities
- `gemma3:3b` - Lightweight option

### Environment Variables

```bash
# Ollama Configuration
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="gpt-oss:20b"
export OLLAMA_TEMPERATURE="0.7"

# Analysis Configuration
export MAX_TURNS="20"
export MAX_STALLS="3"
export OUTPUT_DIR="outputs"
```

---

## 🛠️ Makefile Commands

The Makefile provides convenient commands for common operations:

### Setup & Installation
```bash
make setup          # Complete initial setup (Docker + dependencies)
make local-setup    # Local Python environment setup
```

### Running the Platform
```bash
make run            # Run crypto analysis (Docker, interactive)
make local-run      # Run crypto analysis (local, interactive)
make crypto-interactive  # Advanced analysis mode (Docker)
make local-crypto-interactive  # Advanced analysis mode (local)
```

### Docker Operations
```bash
make start          # Start Docker services
make stop           # Stop Docker services  
make restart        # Restart services
make status         # Check service status
make shell          # Open shell in app container
```

### Monitoring & Logs
```bash
make logs           # View all logs (follow mode)
make logs-app       # View application logs only
```

### Maintenance
```bash
make clean          # Stop services and remove volumes
make rebuild        # Rebuild containers from scratch
make test           # Test platform setup
make pull-model     # Instructions for pulling Ollama models
```

### Testing & Verification
```bash
make local-test     # Run platform verification tests
```

**View all commands:**
```bash
make help
```

---

## 📈 Output Files

All analysis results are saved to the `outputs/` directory:

- **Charts**: `bitcoin_chart_20251127_194512.html` - Interactive Plotly candlestick charts
- **Reports**: `task_output_20251127_193032.txt` - Complete analysis logs
- **Code**: `code_execution/` - Generated Python analysis scripts

**Opening Charts:**
```bash
# macOS
open outputs/bitcoin_chart_*.html

# Linux
xdg-open outputs/bitcoin_chart_*.html

# Or drag-and-drop into browser
```

---

## 🧪 Technical Details

### Data Source
- **API**: CoinGecko Free Tier (no API key required)
- **Rate Limits**: Respectful request spacing (50 calls/minute)
- **Coverage**: 10,000+ cryptocurrencies
- **History**: Up to 365 days of OHLCV data

### Technical Indicators Implementation

| Indicator | Parameters | Calculation |
|-----------|-----------|-------------|
| **RSI** | 14 periods | Relative Strength Index |
| **MACD** | 12, 26, 9 | Moving Average Convergence Divergence |
| **Bollinger Bands** | 20 period, 2σ | Standard deviation bands |
| **SMA** | 20, 50 periods | Simple Moving Average |
| **EMA** | 12, 26 periods | Exponential Moving Average |

### Function Calling

The platform implements native function calling for compatible Ollama models:

**Available Tools:**
- `get_crypto_price(symbol)` - Fetch current price and market data
- `get_historical_data(symbol, days)` - Get OHLCV history
- `get_market_info(symbol)` - Detailed market statistics
- `create_crypto_chart(symbol, days, indicators)` - Generate charts

These tools are automatically discovered and invoked by the AI agents based on user queries.

---

## ⚠️ Important Notes

### Disclaimer

**This platform is for educational and research purposes only.**

- ❌ This is NOT financial advice
- ❌ Do not make investment decisions based solely on this analysis
- ✅ Always conduct your own research (DYOR)
- ✅ Cryptocurrency trading carries substantial risk
- ✅ Past performance does not guarantee future results
- ✅ Consult a qualified financial advisor before investing

### API Rate Limits

CoinGecko's free tier has the following limits:
- 50 calls per minute
- 10,000 calls per month

The platform implements respectful delays, but avoid excessive queries.

### Cryptocurrency ID Format

Use exact CoinGecko IDs (not ticker symbols):
- ✅ `bitcoin` (not `BTC`)
- ✅ `ethereum` (not `ETH`)
- ✅ `avalanche-2` (not `AVAX`)

Check [CoinGecko.com](https://www.coingecko.com) for correct IDs.

---

## 🐛 Troubleshooting

### Ollama Connection Issues

**Problem:** "Connection refused" or "Ollama not responding"

**Solution:**
```bash
# Start Ollama service
ollama serve

# Test connection
curl http://localhost:11434/api/tags
```

### Model Not Found

**Problem:** "Model 'gpt-oss:20b' not found"

**Solution:**
```bash
# Pull the model
ollama pull gpt-oss:20b

# Or use an alternative
ollama pull llama3.2
```

### Import Errors

**Problem:** "ModuleNotFoundError: No module named 'pandas'"

**Solution:**
```bash
# Reinstall dependencies
source .venv/bin/activate
pip install -e .
```

### Chart Generation Failed

**Problem:** Charts not saving or rendering incorrectly

**Solution:**
```bash
# Install chart dependencies
pip install plotly kaleido

# Ensure outputs directory exists
mkdir -p outputs
```

### Docker Issues

**Problem:** Container won't start or crashes

**Solution:**
```bash
# Check logs
make logs-app

# Rebuild containers
make clean
make rebuild

# Verify Ollama on host
curl http://localhost:11434/api/tags
```

### Function Calling Not Working

**Problem:** Agents not using tools properly

**Solution:**
1. Verify model supports function calling (gpt-oss, llama3, mistral)
2. Check `src/config.py` has correct model name
3. Restart Ollama service
4. Review logs for error messages

---

## 🚀 Get Started Now!

```bash
# Quick start (Docker)
make setup && make start && make run

# Or locally
make local-setup && make local-run
```

**Start analyzing crypto markets like a pro! 📈**

---

## 📝 License & Attribution

Built with ❤️ using:
- [MagenticOne](https://github.com/microsoft/autogen) - Multi-agent framework
- [Ollama](https://ollama.ai) - Local LLM runtime
- [CoinGecko API](https://www.coingecko.com) - Cryptocurrency data
- [Plotly](https://plotly.com) - Interactive charting

---

**Questions or Issues?** Check the troubleshooting section or review the platform logs.
