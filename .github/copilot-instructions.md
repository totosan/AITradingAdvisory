# Copilot Instructions - Crypto Analysis Platform

## Architecture Overview

This is a **MagenticOne multi-agent system** specialized for cryptocurrency analysis. The platform uses AutoGen's orchestrator pattern where specialized AI agents collaborate to analyze crypto markets.

### Key Components

- **MagenticOneGroupChat**: Orchestrator that coordinates 6 specialized agents
- **Agents**: Each has specific expertise, tools, and system prompts
  - `CryptoMarketAnalyst` - Fetches prices, market data (uses crypto_tools + exchange_tools)
  - `TechnicalAnalyst` - Charts, indicators, signals, custom indicator design
  - `ChartingAgent` - TradingView charts, multi-timeframe dashboards, smart alerts
  - `CryptoAnalysisCoder` - Writes Python scripts, implements custom indicators
  - `ReportWriter` - Creates professional Markdown reports
  - `Executor` (CodeExecutorAgent) - Runs generated code in isolated environment
- **Ollama/Azure Client**: LLM integration with function calling support
- **Data Sources**: Bitget Exchange (real-time) + CoinGecko API (historical)

### Critical Data Flow

```
User Query → MagenticOneGroupChat → Agent Selection → Tool Execution → Ollama LLM → Response
```

The orchestrator uses `max_turns=20` and `max_stalls=3` to prevent infinite loops. Agents are selected based on task relevance, not round-robin.

## Function Calling Pattern

**Critical**: This codebase implements custom function calling for Ollama models. In `src/ollama_client.py`:

```python
# Function definitions use Annotated for descriptions
def get_crypto_price(
    symbol: Annotated[str, "The cryptocurrency symbol (e.g., 'bitcoin', 'ethereum')"]
) -> str:
    ...

# OllamaChatCompletionClient extracts these at runtime
capabilities = {"function_calling": True}  # Only for supported models
```

When adding new tools:
1. Use `Annotated[type, "description"]` for parameters
2. Add function to agent's `tools=[]` list
3. Document in agent's `system_message`
4. Function must return `str` (JSON for structured data)

**Supported models**: gpt-oss:20b, llama3, mistral, mixtral (check `capabilities` property)

## Development Workflow

### Running the Platform

```bash
# Docker (recommended)
make setup && make start && make run

# Local (requires Ollama running)
make local-setup  # Uses UV
make local-run
```

### Environment Configuration

Set model in `src/config.py` or via environment:
```bash
export LLM_PROVIDER="ollama"  # or "azure"
export OLLAMA_MODEL="gpt-oss:20b"
export OLLAMA_BASE_URL="http://localhost:11434"
export MAX_TURNS="20"
```

Docker uses `host.docker.internal:11434` to access host Ollama.

## Code Conventions

### Agent System Messages

Follow existing pattern in `src/main.py`:
- **Role definition**: Expertise and specialization
- **Responsibilities**: 3-5 numbered tasks
- **Tool usage**: List tools with signatures
- **Guidelines**: Specific thresholds (e.g., "RSI < 30 = Oversold")

### Tool Functions (src/crypto_tools.py)

```python
def get_crypto_price(
    symbol: Annotated[str, "Exact description for LLM"],
) -> str:  # Always return str
    """
    Docstring appears in function schema.
    Include Args and Returns.
    """
    try:
        # CoinGecko API call
        return json.dumps(result)  # JSON string for structured data
    except Exception as e:
        return f"Error: {str(e)}"  # Always handle errors
```

### Output Files

All generated files go to `outputs/`:
- Charts: `{coin}_chart_{timestamp}.html`
- Logs: `task_output_{timestamp}.txt`
- Code: `outputs/code_execution/`

Use `Path(config.output_dir)` not hardcoded paths.

## Dependencies & External Services

### CoinGecko API (Free Tier)
- **No API key required**
- Base URL: `https://api.coingecko.com/api/v3`
- Rate limit: ~50 calls/minute (free tier)
- Use exact coin IDs: `bitcoin`, `ethereum`, `avalanche-2` (not ticker symbols)

### Python Dependencies
- `autogen-agentchat>=0.4.0` - Core agent framework
- `autogen-ext[magentic-one]>=0.4.0` - MagenticOne team
- `pandas`, `numpy` - Technical indicator calculations
- `plotly`, `kaleido` - Interactive chart generation
- `requests`, `aiohttp` - API calls

### Ollama Models
Tested with:
- `gpt-oss:20b` (recommended, function calling)
- `llama3.2`, `deepseek-r1:1.5b`, `mistral`

Pull via: `ollama pull gpt-oss:20b`

## Common Pitfalls

1. **Function calling not working**: Check model in `ollama_client.py` capabilities list
2. **"Model not found"**: Run `ollama pull <model>` on host (not in Docker)
3. **Docker Exit 137**: Out of memory - reduce `max_turns` or use lighter model
4. **CoinGecko errors**: Use exact coin IDs from their API, not ticker symbols
5. **Import errors**: Run `uv pip install -e .` to install in editable mode

## Key Files Reference

- `src/main.py` - Main entry point, agent definitions, conversation mode
- `src/config.py` - Configuration dataclasses (env-based)
- `src/ollama_client.py` - Custom ChatCompletionClient with function calling
- `src/crypto_tools.py` - CoinGecko data fetching and indicator calculations
- `src/crypto_charts.py` - Plotly chart generation
- `src/exchange_tools.py` - Bitget exchange integration
- `src/tradingview_tools.py` - TradingView-style chart generation
- `src/smart_alerts.py` - AI-powered alert dashboard
- `src/report_tools.py` - Markdown report generation
- `src/indicator_registry.py` - Persistent custom indicators
- `src/exchange_providers/` - Exchange abstraction layer
- `Makefile` - All commands (run `make help`)
