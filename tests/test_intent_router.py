"""
Tests for Intent Router module.
"""
import pytest
from src.intent_router import (
    IntentRouter,
    IntentType,
    Intent,
    format_simple_result,
)


class TestIntentClassification:
    """Tests for intent classification."""
    
    @pytest.fixture
    def router(self):
        """Create a fresh router for each test."""
        return IntentRouter()
    
    # Simple lookup tests
    def test_simple_price_query(self, router):
        """Test that simple price queries are classified as SIMPLE_LOOKUP."""
        simple_queries = [
            "What is the price of Bitcoin?",
            "What's the price of ETH?",
            "BTC price?",
            "Price of Solana",
            "Get price of ETH",
            "Show me the price of BTC",
            "How much is Bitcoin?",
            "How much does Ethereum cost?",
        ]
        
        for query in simple_queries:
            intent = router.classify(query)
            assert intent.type == IntentType.SIMPLE_LOOKUP, f"Failed for: {query}"
            assert intent.confidence >= 0.6, f"Low confidence for: {query}"
    
    def test_simple_lookup_extracts_symbols(self, router):
        """Test that symbols are extracted from simple queries."""
        intent = router.classify("What is the price of Bitcoin?")
        assert "BTCUSDT" in intent.entities.get("symbols", [])
        
        intent = router.classify("ETH price?")
        assert "ETHUSDT" in intent.entities.get("symbols", [])
    
    # Analysis intent tests
    def test_analysis_queries(self, router):
        """Test that analysis queries are classified correctly."""
        analysis_queries = [
            "What is the current situation of BTC?",
            "Analyze Bitcoin for me",
            "Give me a technical analysis of ETH",
            "What do you think about Solana?",
            "Should I buy BTC now?",
            "What's the outlook for Ethereum?",
            "Provide trading signals for BTC",
            "What are the support and resistance levels for ETH?",
        ]
        
        for query in analysis_queries:
            intent = router.classify(query)
            assert intent.type == IntentType.ANALYSIS, f"Failed for: {query}"
    
    def test_chart_queries(self, router):
        """Test that chart queries are classified correctly."""
        chart_queries = [
            "Create a chart for BTC",
            "Generate a candlestick chart for ETH",
            "Show me a dashboard for Solana",
            "Visualize BTC price action",
        ]
        
        for query in chart_queries:
            intent = router.classify(query)
            assert intent.type == IntentType.CHART, f"Failed for: {query}"
    
    def test_comparison_queries(self, router):
        """Test that comparison queries are classified correctly."""
        comparison_queries = [
            "Compare BTC to ETH",
            "BTC vs ETH",
            "Which is better, Bitcoin or Ethereum?",
            "What's the difference between SOL and ETH?",
        ]
        
        for query in comparison_queries:
            intent = router.classify(query)
            assert intent.type == IntentType.COMPARISON, f"Failed for: {query}"
    
    def test_report_queries(self, router):
        """Test that report queries are classified correctly."""
        # Note: queries containing "analysis" may be classified as ANALYSIS
        # due to the analysis trigger taking precedence
        report_queries = [
            ("Create a report on Bitcoin", IntentType.REPORT),
            ("Generate a summary report for ETH", IntentType.REPORT),
            ("Write a report about Solana", IntentType.REPORT),
            # This one contains "analysis" so it goes to ANALYSIS
            ("Generate an analysis report for ETH", IntentType.ANALYSIS),
        ]
        
        for query, expected_type in report_queries:
            intent = router.classify(query)
            assert intent.type == expected_type, f"Failed for: {query}, got {intent.type}"
    
    # Edge cases
    def test_empty_message(self, router):
        """Test handling of empty message."""
        intent = router.classify("")
        assert intent.type == IntentType.CONVERSATION
        assert intent.confidence == 1.0
    
    def test_ambiguous_defaults_to_analysis(self, router):
        """Test that ambiguous queries default to analysis."""
        intent = router.classify("Tell me everything about crypto markets")
        # Should either be analysis or have lower confidence
        assert intent.type in [IntentType.ANALYSIS, IntentType.CONVERSATION]
    
    def test_mixed_intent_prefers_analysis(self, router):
        """Test that mixed intent with analysis triggers goes to analysis."""
        # Contains both "price" and "analysis" triggers
        intent = router.classify("What is the price situation and trend for BTC?")
        assert intent.type == IntentType.ANALYSIS


class TestIntentIsSimple:
    """Tests for Intent.is_simple() method."""
    
    def test_simple_with_high_confidence(self):
        """Test that high confidence SIMPLE_LOOKUP is considered simple."""
        intent = Intent(
            type=IntentType.SIMPLE_LOOKUP,
            confidence=0.9,
            entities={"symbols": ["BTCUSDT"]},
        )
        assert intent.is_simple() is True
    
    def test_simple_with_low_confidence(self):
        """Test that low confidence SIMPLE_LOOKUP is not considered simple."""
        intent = Intent(
            type=IntentType.SIMPLE_LOOKUP,
            confidence=0.5,
            entities={"symbols": ["BTCUSDT"]},
        )
        assert intent.is_simple() is False
    
    def test_analysis_is_not_simple(self):
        """Test that ANALYSIS intent is not considered simple."""
        intent = Intent(
            type=IntentType.ANALYSIS,
            confidence=0.9,
            entities={"symbols": ["BTCUSDT"]},
        )
        assert intent.is_simple() is False


class TestSymbolExtraction:
    """Tests for cryptocurrency symbol extraction."""
    
    @pytest.fixture
    def router(self):
        return IntentRouter()
    
    def test_extracts_btc(self, router):
        """Test BTC symbol extraction."""
        intent = router.classify("Price of BTC")
        assert "BTCUSDT" in intent.entities.get("symbols", [])
    
    def test_extracts_bitcoin(self, router):
        """Test Bitcoin full name extraction."""
        intent = router.classify("Price of Bitcoin")
        assert "BTCUSDT" in intent.entities.get("symbols", [])
    
    def test_extracts_multiple_symbols(self, router):
        """Test multiple symbol extraction."""
        intent = router.classify("Compare BTC and ETH")
        symbols = intent.entities.get("symbols", [])
        assert "BTCUSDT" in symbols
        assert "ETHUSDT" in symbols
    
    def test_no_symbols_in_general_query(self, router):
        """Test that general queries may not have symbols."""
        intent = router.classify("How does crypto work?")
        # Should still work, just might not have symbols
        assert isinstance(intent.entities.get("symbols", []), list)


class TestLLMClassification:
    """Tests for LLM-based intent classification (pattern fallback)."""
    
    def test_router_without_llm_uses_patterns(self):
        """Test that router falls back to patterns when LLM is disabled."""
        router = IntentRouter(use_llm=False)
        
        intent = router.classify("What is the price of BTC?")
        assert intent.type == IntentType.SIMPLE_LOOKUP
        assert "Pattern" in intent.reason or "pattern" in intent.reason
    
    def test_router_with_no_client_uses_patterns(self):
        """Test that router uses patterns when no model client is provided."""
        router = IntentRouter(model_client=None, use_llm=True)
        # The classify method should fall back to patterns
        intent = router.classify("What is the price of BTC?")
        assert intent.type == IntentType.SIMPLE_LOOKUP
    
    @pytest.mark.asyncio
    async def test_async_classify_falls_back_to_patterns(self):
        """Test that async classify falls back to patterns when LLM unavailable."""
        router = IntentRouter(model_client=None, use_llm=True)
        
        # Even with use_llm=True, if no client available, should use patterns
        intent = await router.classify_async("What is the price of BTC?")
        assert intent.type == IntentType.SIMPLE_LOOKUP
        assert intent.entities.get("symbols") == ["BTCUSDT"]
    
    @pytest.mark.asyncio
    async def test_async_classify_analysis_intent(self):
        """Test that async classify correctly identifies analysis intent."""
        router = IntentRouter(use_llm=False)  # Force pattern-based
        
        intent = await router.classify_async("What is the current situation of BTC?")
        assert intent.type == IntentType.ANALYSIS
        assert intent.entities.get("symbols") == ["BTCUSDT"]


class TestCompoundIntents:
    """Tests for compound intent detection and decomposition."""
    
    @pytest.fixture
    def router(self):
        """Create a router with LLM disabled for deterministic testing."""
        return IntentRouter(use_llm=False)
    
    def test_price_and_chart_compound(self, router):
        """Test detecting price + chart compound query."""
        intent = router.classify("What is the price of BTC and show me a chart?")
        
        # Primary should be CHART (more complex)
        assert intent.type == IntentType.CHART
        # Sub-intent should include SIMPLE_LOOKUP
        assert IntentType.SIMPLE_LOOKUP in intent.sub_intents
        assert intent.is_compound()
        assert intent.has_quick_component()
    
    def test_price_and_analysis_compound(self, router):
        """Test detecting price + analysis compound query."""
        intent = router.classify("Show me the current price of ETH and analyze it")
        
        # Primary should be ANALYSIS (more complex)
        assert intent.type == IntentType.ANALYSIS
        # Sub-intent should include SIMPLE_LOOKUP
        assert IntentType.SIMPLE_LOOKUP in intent.sub_intents
        assert intent.has_quick_component()
    
    def test_simple_query_not_compound(self, router):
        """Test that simple queries are not marked as compound."""
        intent = router.classify("What is the price of BTC?")
        
        assert intent.type == IntentType.SIMPLE_LOOKUP
        assert not intent.is_compound()
        assert not intent.has_quick_component()
    
    def test_analysis_query_not_compound(self, router):
        """Test that pure analysis queries are not compound."""
        intent = router.classify("Analyze the BTC situation")
        
        assert intent.type == IntentType.ANALYSIS
        assert not intent.is_compound()
        assert not intent.has_quick_component()
    
    def test_chart_and_analysis_no_quick_component(self, router):
        """Test that chart + analysis without price has no quick component."""
        intent = router.classify("Create a chart and analyze BTC trends")
        
        # Should be ANALYSIS (higher priority)
        assert intent.type == IntentType.ANALYSIS
        # CHART is a sub-intent but not SIMPLE_LOOKUP
        assert IntentType.CHART in intent.sub_intents
        assert not intent.has_quick_component()  # No price lookup
    
    def test_compound_extracts_symbols(self, router):
        """Test that compound queries still extract symbols correctly."""
        intent = router.classify("BTC price and chart please")
        
        assert "BTCUSDT" in intent.entities.get("symbols", [])
        assert intent.is_compound()


class TestFormatSimpleResult:
    """Tests for result formatting."""
    
    def test_format_success_with_price(self):
        """Test formatting a successful price result."""
        result = {
            "success": True,
            "results": [{"symbol": "BTCUSDT", "data": '{"price": 45000.50, "change_24h": 2.5}'}],
            "symbols": ["BTCUSDT"],
            "tool_used": "get_realtime_price",
        }
        
        formatted = format_simple_result(result)
        assert "BTCUSDT" in formatted
        assert "45,000.5000" in formatted  # 4 decimal places
        assert "📈" in formatted  # Positive change emoji
    
    def test_format_success_with_negative_change(self):
        """Test formatting with negative price change."""
        result = {
            "success": True,
            "results": [{"symbol": "BTCUSDT", "data": '{"price": 45000.50, "change_24h": -3.2}'}],
            "symbols": ["BTCUSDT"],
            "tool_used": "get_realtime_price",
        }
        
        formatted = format_simple_result(result)
        assert "📉" in formatted  # Negative change emoji
    
    def test_format_small_price(self):
        """Test formatting a small crypto price with more decimals."""
        result = {
            "success": True,
            "results": [{"symbol": "DOGEUSDT", "data": '{"price": 0.0823, "change_24h": 1.5}'}],
            "symbols": ["DOGEUSDT"],
            "tool_used": "get_realtime_price",
        }
        
        formatted = format_simple_result(result)
        assert "DOGEUSDT" in formatted
        assert "0.0823" in formatted  # 4 decimal places preserved
    
    def test_format_very_small_price(self):
        """Test formatting a very small crypto price with 6 decimals."""
        result = {
            "success": True,
            "results": [{"symbol": "SHIBUSDT", "data": '{"price": 0.00001234, "change_24h": -0.5}'}],
            "symbols": ["SHIBUSDT"],
            "tool_used": "get_realtime_price",
        }
        
        formatted = format_simple_result(result)
        assert "SHIBUSDT" in formatted
        assert "0.000012" in formatted  # 6 decimal places for tiny prices
    
    def test_format_multiple_symbols(self):
        """Test formatting multiple symbol results."""
        result = {
            "success": True,
            "results": [
                {"symbol": "BTCUSDT", "data": '{"price": 45000, "change_24h": 2.5}'},
                {"symbol": "ETHUSDT", "data": '{"price": 2500, "change_24h": -1.2}'},
                {"symbol": "SOLUSDT", "data": '{"price": 100, "change_24h": 5.0}'},
            ],
            "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "tool_used": "get_realtime_price",
        }
        
        formatted = format_simple_result(result)
        assert "BTCUSDT" in formatted
        assert "ETHUSDT" in formatted
        assert "SOLUSDT" in formatted
        assert "45,000" in formatted
        assert "2,500" in formatted
    
    def test_format_error(self):
        """Test formatting an error result."""
        result = {
            "success": False,
            "error": "Symbol not found",
        }
        
        formatted = format_simple_result(result)
        assert "❌" in formatted
        assert "Symbol not found" in formatted
    
    def test_format_raw_string_result(self):
        """Test formatting when result is a plain string."""
        result = {
            "success": True,
            "results": [{"symbol": "BTCUSDT", "data": "Price: $45,000"}],
            "symbols": ["BTCUSDT"],
        }
        
        formatted = format_simple_result(result)
        assert "Price: $45,000" in formatted


class TestToolRegistration:
    """Tests for tool registration and execution."""
    
    @pytest.fixture
    def router(self):
        return IntentRouter()
    
    def test_register_tool(self, router):
        """Test registering a tool function."""
        def mock_tool(symbol: str) -> str:
            return f'{{"price": 100, "symbol": "{symbol}"}}'
        
        router.register_tool("mock_tool", mock_tool)
        assert "mock_tool" in router.tools
    
    def test_execute_simple_with_registered_tool(self, router):
        """Test executing a simple intent with registered tool."""
        import asyncio
        
        def mock_price(symbol: str) -> str:
            return '{"price": 50000, "change_24h": 1.5}'
        
        router.register_tool("get_realtime_price", mock_price)
        
        intent = Intent(
            type=IntentType.SIMPLE_LOOKUP,
            confidence=0.9,
            entities={"symbols": ["BTCUSDT"]},
            tool_hint="get_realtime_price",
        )
        
        result = asyncio.get_event_loop().run_until_complete(
            router.execute_simple("BTC price", intent)
        )
        
        assert result["success"] is True
        assert "BTCUSDT" in result["symbols"]
        assert result["tool_used"] == "get_realtime_price"
        assert len(result["results"]) == 1
    
    def test_execute_simple_multiple_symbols(self, router):
        """Test executing a simple intent with multiple symbols."""
        import asyncio
        
        def mock_price(symbol: str) -> str:
            prices = {"BTCUSDT": 50000, "ETHUSDT": 2500, "SOLUSDT": 100}
            price = prices.get(symbol, 0)
            return f'{{"price": {price}, "change_24h": 1.5}}'
        
        router.register_tool("get_realtime_price", mock_price)
        
        intent = Intent(
            type=IntentType.SIMPLE_LOOKUP,
            confidence=0.9,
            entities={"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]},
            tool_hint="get_realtime_price",
        )
        
        result = asyncio.get_event_loop().run_until_complete(
            router.execute_simple("BTC ETH SOL prices", intent)
        )
        
        assert result["success"] is True
        assert len(result["results"]) == 3
        assert result["symbols"] == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    def test_execute_simple_without_tool(self, router):
        """Test execution fails gracefully when tool is missing."""
        import asyncio
        
        intent = Intent(
            type=IntentType.SIMPLE_LOOKUP,
            confidence=0.9,
            entities={"symbols": ["BTCUSDT"]},
            tool_hint="nonexistent_tool",
        )
        
        result = asyncio.get_event_loop().run_until_complete(
            router.execute_simple("BTC price", intent)
        )
        
        assert result["success"] is False
        assert result["fallback_to_agents"] is True
    
    def test_execute_simple_without_symbols(self, router):
        """Test execution fails when no symbols found."""
        import asyncio
        
        intent = Intent(
            type=IntentType.SIMPLE_LOOKUP,
            confidence=0.9,
            entities={"symbols": []},  # No symbols
            tool_hint="get_realtime_price",
        )
        
        result = asyncio.get_event_loop().run_until_complete(
            router.execute_simple("price please", intent)
        )
        
        assert result["success"] is False
        assert result["fallback_to_agents"] is True
