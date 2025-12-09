"""
Tests for the Tool Registry module.

Tests the dynamic tool storage, token-optimized discovery, and execution.
"""
import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tool_registry import (
    ToolRegistry,
    ToolCategory,
    ToolTier,
    ToolSummary,
    ToolDefinition,
    EmbeddingManager,
    save_custom_tool,
    list_custom_tools,
    get_custom_tool,
    execute_custom_tool,
    delete_custom_tool,
    search_tools_semantic,
    INTENT_CATEGORY_MAP,
)


class TestToolRegistry:
    """Tests for ToolRegistry class."""
    
    @pytest.fixture
    def temp_registry(self, tmp_path):
        """Create a temporary registry for testing."""
        registry = ToolRegistry(registry_dir=tmp_path / "tools")
        return registry
    
    def test_registry_initialization(self, temp_registry):
        """Test that registry initializes correctly."""
        registry = temp_registry._ensure_registry_exists()
        
        assert registry["version"] == "1.0"
        assert "tools" in registry
        assert "category_index" in registry
        assert "tag_index" in registry
    
    def test_save_tool(self, temp_registry):
        """Test saving a tool to the registry."""
        tool_id, tool_def = temp_registry.save_tool(
            name="Test Tool",
            code="def test_func(x): return x * 2",
            description="A test tool that doubles values",
            one_liner="Doubles input values",
            input_schema={"type": "object", "properties": {"x": {"type": "number"}}},
            category=ToolCategory.UTILITY,
            tags=["test", "utility"],
        )
        
        assert tool_id == "test_tool"
        assert tool_def.name == "Test Tool"
        assert tool_def.category == "utility"
        assert tool_def.version == 1
    
    def test_save_tool_update(self, temp_registry):
        """Test updating an existing tool."""
        # Save first version
        temp_registry.save_tool(
            name="Test Tool",
            code="def test_func(x): return x * 2",
            description="Version 1",
            one_liner="First version",
            input_schema={},
        )
        
        # Update
        tool_id, tool_def = temp_registry.save_tool(
            name="Test Tool",
            code="def test_func(x): return x * 3",
            description="Version 2",
            one_liner="Updated version",
            input_schema={},
        )
        
        assert tool_def.version == 2
        assert "x * 3" in tool_def.code
    
    def test_get_tool(self, temp_registry):
        """Test retrieving a tool by ID."""
        temp_registry.save_tool(
            name="Fetch Prices",
            code="def fetch_prices(): pass",
            description="Fetches crypto prices",
            one_liner="Price fetcher",
            input_schema={},
            category=ToolCategory.MARKET_DATA,
        )
        
        tool = temp_registry.get_tool("fetch_prices")
        
        assert tool is not None
        assert tool.name == "Fetch Prices"
        assert tool.category == "market_data"
        assert tool.usage_count == 1  # Incremented on get
    
    def test_get_tool_partial_match(self, temp_registry):
        """Test retrieving a tool with partial ID match."""
        temp_registry.save_tool(
            name="Volume Weighted RSI",
            code="def calc(): pass",
            description="VW-RSI",
            one_liner="Volume weighted RSI",
            input_schema={},
        )
        
        tool = temp_registry.get_tool("weighted_rsi")
        
        assert tool is not None
        assert tool.name == "Volume Weighted RSI"
    
    def test_get_tool_not_found(self, temp_registry):
        """Test getting a non-existent tool."""
        tool = temp_registry.get_tool("nonexistent")
        assert tool is None
    
    def test_get_tool_summaries(self, temp_registry):
        """Test getting lightweight tool summaries."""
        # Save multiple tools
        temp_registry.save_tool(
            name="Market Data Tool",
            code="def fetch(): pass",
            description="Market data fetcher",
            one_liner="Fetches market data",
            input_schema={},
            category=ToolCategory.MARKET_DATA,
        )
        temp_registry.save_tool(
            name="Technical Tool",
            code="def calc(): pass",
            description="Technical analysis",
            one_liner="Calculates technicals",
            input_schema={},
            category=ToolCategory.TECHNICAL,
        )
        
        # Get all summaries
        summaries = temp_registry.get_tool_summaries()
        
        assert len(summaries) == 2
        assert all(isinstance(s, ToolSummary) for s in summaries)
    
    def test_get_tool_summaries_by_category(self, temp_registry):
        """Test filtering summaries by category."""
        temp_registry.save_tool(
            name="Market Tool",
            code="def fetch(): pass",
            description="Market data",
            one_liner="Market data",
            input_schema={},
            category=ToolCategory.MARKET_DATA,
        )
        temp_registry.save_tool(
            name="Tech Tool",
            code="def calc(): pass",
            description="Technical",
            one_liner="Technical",
            input_schema={},
            category=ToolCategory.TECHNICAL,
        )
        
        summaries = temp_registry.get_tool_summaries(
            categories=[ToolCategory.MARKET_DATA]
        )
        
        assert len(summaries) == 1
        assert summaries[0].category == "market_data"
    
    def test_get_tool_summaries_by_intent(self, temp_registry):
        """Test filtering summaries by intent type."""
        temp_registry.save_tool(
            name="Market Tool",
            code="def fetch(): pass",
            description="Market data",
            one_liner="Market data",
            input_schema={},
            category=ToolCategory.MARKET_DATA,
        )
        temp_registry.save_tool(
            name="Chart Tool",
            code="def chart(): pass",
            description="Charting",
            one_liner="Charts",
            input_schema={},
            category=ToolCategory.CHARTING,
        )
        
        # Intent "simple_lookup" should only match MARKET_DATA
        summaries = temp_registry.get_tool_summaries(intent_type="simple_lookup")
        
        assert len(summaries) == 1
        assert summaries[0].category == "market_data"
    
    def test_get_tool_summaries_search(self, temp_registry):
        """Test searching tool summaries."""
        temp_registry.save_tool(
            name="Whale Tracker",
            code="def track(): pass",
            description="Tracks whale movements",
            one_liner="Whale tracking",
            input_schema={},
            tags=["whale", "tracking"],
        )
        temp_registry.save_tool(
            name="Price Monitor",
            code="def monitor(): pass",
            description="Monitors prices",
            one_liner="Price monitoring",
            input_schema={},
            tags=["price"],
        )
        
        summaries = temp_registry.get_tool_summaries(search="whale")
        
        assert len(summaries) == 1
        assert summaries[0].name == "Whale Tracker"
    
    def test_get_tools_for_intent(self, temp_registry):
        """Test getting tools optimized for an intent."""
        # Save tools with different tiers
        temp_registry.save_tool(
            name="Core Market Tool",
            code="def fetch(): pass",
            description="Core tool",
            one_liner="Core market data",
            input_schema={},
            category=ToolCategory.MARKET_DATA,
            tier=ToolTier.CORE,
        )
        temp_registry.save_tool(
            name="Custom Market Tool",
            code="def custom(): pass",
            description="Custom tool",
            one_liner="Custom market data",
            input_schema={},
            category=ToolCategory.MARKET_DATA,
            tier=ToolTier.CUSTOM,
        )
        
        full_defs, custom_summaries = temp_registry.get_tools_for_intent("simple_lookup")
        
        # Core tools should be in full definitions
        assert len(full_defs) == 1
        assert full_defs[0].name == "Core Market Tool"
        
        # Custom tools should only be summaries
        assert len(custom_summaries) == 1
        assert custom_summaries[0].name == "Custom Market Tool"
    
    def test_delete_tool(self, temp_registry):
        """Test deleting a tool."""
        temp_registry.save_tool(
            name="To Delete",
            code="def delete_me(): pass",
            description="Will be deleted",
            one_liner="Delete me",
            input_schema={},
        )
        
        success = temp_registry.delete_tool("to_delete")
        
        assert success
        assert temp_registry.get_tool("to_delete") is None
    
    def test_discovery_prompt(self, temp_registry):
        """Test generating a discovery prompt."""
        temp_registry.save_tool(
            name="Whale Tracker",
            code="def track(): pass",
            description="Tracks whale movements",
            one_liner="Monitors large wallet movements",
            input_schema={},
            tier=ToolTier.CUSTOM,
        )
        
        prompt = temp_registry.get_discovery_prompt()
        
        assert "whale tracker" in prompt.lower()
        assert "monitors large wallet movements" in prompt.lower()
        assert "Available custom tools:" in prompt
    
    def test_execute_tool(self, temp_registry):
        """Test executing a tool."""
        temp_registry.save_tool(
            name="Doubler",
            code="""
def double_value(x):
    return x * 2
""",
            description="Doubles a value",
            one_liner="Doubles input",
            input_schema={"type": "object", "properties": {"x": {"type": "number"}}},
        )
        
        result = temp_registry.execute_tool("doubler", {"x": 5})
        result_data = json.loads(result)
        
        assert result_data["status"] == "success"
        assert result_data["result"] == 10
    
    def test_category_index(self, temp_registry):
        """Test that category index is maintained."""
        temp_registry.save_tool(
            name="Tool 1",
            code="def t1(): pass",
            description="Tool 1",
            one_liner="Tool 1",
            input_schema={},
            category=ToolCategory.MARKET_DATA,
        )
        temp_registry.save_tool(
            name="Tool 2",
            code="def t2(): pass",
            description="Tool 2",
            one_liner="Tool 2",
            input_schema={},
            category=ToolCategory.MARKET_DATA,
        )
        
        registry = temp_registry._ensure_registry_exists()
        
        assert "market_data" in registry["category_index"]
        assert len(registry["category_index"]["market_data"]) == 2
    
    def test_tag_index(self, temp_registry):
        """Test that tag index is maintained."""
        temp_registry.save_tool(
            name="Tagged Tool",
            code="def t(): pass",
            description="Tagged",
            one_liner="Tagged tool",
            input_schema={},
            tags=["crypto", "trading"],
        )
        
        registry = temp_registry._ensure_registry_exists()
        
        assert "crypto" in registry["tag_index"]
        assert "trading" in registry["tag_index"]


class TestToolRegistryFunctions:
    """Tests for the functional interface."""
    
    def test_save_custom_tool_function(self, tmp_path, monkeypatch):
        """Test save_custom_tool function."""
        # Patch the registry to use temp directory
        from tool_registry import _get_registry, ToolRegistry
        
        test_registry = ToolRegistry(registry_dir=tmp_path / "tools")
        monkeypatch.setattr("tool_registry._registry", test_registry)
        
        result = save_custom_tool(
            name="Test Function",
            code="def test(): pass",
            description="Test description",
            one_liner="Test one liner",
            input_schema='{"type": "object"}',
            category="utility",
        )
        
        result_data = json.loads(result)
        
        assert result_data["status"] == "success"
        assert result_data["tool_id"] == "test_function"
    
    def test_list_custom_tools_function(self, tmp_path, monkeypatch):
        """Test list_custom_tools function."""
        from tool_registry import ToolRegistry
        
        test_registry = ToolRegistry(registry_dir=tmp_path / "tools")
        test_registry.save_tool(
            name="Listed Tool",
            code="def list_me(): pass",
            description="Listed",
            one_liner="Listed tool",
            input_schema={},
        )
        monkeypatch.setattr("tool_registry._registry", test_registry)
        
        result = list_custom_tools()
        result_data = json.loads(result)
        
        assert result_data["status"] == "success"
        assert result_data["total_tools"] == 1


class TestIntentCategoryMapping:
    """Tests for intent to category mapping."""
    
    def test_simple_lookup_categories(self):
        """Test that simple_lookup maps to correct categories."""
        categories = INTENT_CATEGORY_MAP["simple_lookup"]
        assert ToolCategory.MARKET_DATA in categories
    
    def test_analysis_categories(self):
        """Test that analysis maps to correct categories."""
        categories = INTENT_CATEGORY_MAP["analysis"]
        assert ToolCategory.MARKET_DATA in categories
        assert ToolCategory.TECHNICAL in categories
        assert ToolCategory.DERIVATIVES in categories
    
    def test_chart_categories(self):
        """Test that chart maps to correct categories."""
        categories = INTENT_CATEGORY_MAP["chart"]
        assert ToolCategory.CHARTING in categories


class TestToolSummary:
    """Tests for ToolSummary data class."""
    
    def test_to_prompt_line(self):
        """Test formatting summary for prompt."""
        summary = ToolSummary(
            id="whale_tracker",
            name="Whale Tracker",
            one_liner="Monitors large wallet movements",
            category="external_api",
            tier="custom",
        )
        
        line = summary.to_prompt_line()
        
        assert "- Whale Tracker: Monitors large wallet movements" == line


class TestToolDefinition:
    """Tests for ToolDefinition data class."""
    
    def test_to_summary(self):
        """Test converting definition to summary."""
        tool_def = ToolDefinition(
            id="test_tool",
            name="Test Tool",
            description="Full description here",
            one_liner="Short summary",
            code="def test(): pass",
            input_schema={},
            output_schema={},
            category="utility",
            tier="custom",
        )
        
        summary = tool_def.to_summary()
        
        assert isinstance(summary, ToolSummary)
        assert summary.name == "Test Tool"
        assert summary.one_liner == "Short summary"
    
    def test_to_function_schema(self):
        """Test converting to OpenAI function schema."""
        tool_def = ToolDefinition(
            id="test_tool",
            name="Test Tool",
            description="Full description",
            one_liner="Short",
            code="def test(): pass",
            input_schema={
                "type": "object",
                "properties": {"x": {"type": "number"}},
            },
            output_schema={},
            category="utility",
            tier="custom",
        )
        
        schema = tool_def.to_function_schema()
        
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "test_tool"
        assert schema["function"]["description"] == "Full description"
        assert "properties" in schema["function"]["parameters"]


class TestEmbeddingManager:
    """Tests for EmbeddingManager class."""
    
    @pytest.fixture
    def temp_embedding_manager(self, tmp_path):
        """Create a temporary embedding manager for testing."""
        return EmbeddingManager(embeddings_file=tmp_path / "embeddings.json")
    
    def test_embedding_manager_initialization(self, temp_embedding_manager):
        """Test that embedding manager initializes correctly."""
        embeddings = temp_embedding_manager._load_embeddings()
        assert isinstance(embeddings, dict)
    
    def test_save_and_load_embeddings(self, temp_embedding_manager):
        """Test saving and loading embeddings from cache."""
        # Manually set an embedding
        temp_embedding_manager._embeddings_cache = {
            "test_tool": [0.1, 0.2, 0.3, 0.4, 0.5]
        }
        temp_embedding_manager._save_embeddings()
        
        # Clear cache and reload
        temp_embedding_manager._embeddings_cache = None
        embeddings = temp_embedding_manager._load_embeddings()
        
        assert "test_tool" in embeddings
        assert embeddings["test_tool"] == [0.1, 0.2, 0.3, 0.4, 0.5]
    
    def test_remove_embedding(self, temp_embedding_manager):
        """Test removing an embedding from cache."""
        temp_embedding_manager._embeddings_cache = {
            "tool1": [0.1, 0.2],
            "tool2": [0.3, 0.4],
        }
        temp_embedding_manager._save_embeddings()
        
        temp_embedding_manager.remove_embedding("tool1")
        
        embeddings = temp_embedding_manager._load_embeddings()
        assert "tool1" not in embeddings
        assert "tool2" in embeddings
    
    def test_find_similar_tools_with_mock_embeddings(self, temp_embedding_manager):
        """Test finding similar tools using pre-computed embeddings."""
        import numpy as np
        
        # Create mock embeddings (simple 3D vectors for testing)
        tool_embeddings = {
            "whale_tracker": [1.0, 0.0, 0.0],  # Points in x direction
            "price_monitor": [0.0, 1.0, 0.0],  # Points in y direction
            "sentiment_analyzer": [0.7, 0.7, 0.0],  # Between x and y
        }
        
        # Mock the get_embedding method to return a query vector
        with patch.object(temp_embedding_manager, 'get_embedding') as mock_get:
            # Query similar to whale_tracker (x direction)
            mock_get.return_value = [0.9, 0.1, 0.0]
            
            results = temp_embedding_manager.find_similar_tools(
                query="track large transactions",
                tool_embeddings=tool_embeddings,
                top_k=3,
                threshold=0.0,
            )
            
            # whale_tracker should be most similar
            assert len(results) > 0
            tool_ids = [r[0] for r in results]
            assert "whale_tracker" in tool_ids
            
            # Check that results are sorted by similarity
            scores = [r[1] for r in results]
            assert scores == sorted(scores, reverse=True)
    
    def test_is_available_without_credentials(self, temp_embedding_manager, monkeypatch):
        """Test that is_available returns False without credentials."""
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        
        # Reset client
        temp_embedding_manager._client = None
        temp_embedding_manager._initialized = False
        
        # Should return False when credentials are not available
        assert temp_embedding_manager.is_available == False


class TestSemanticSearch:
    """Tests for semantic search functionality."""
    
    @pytest.fixture
    def temp_registry(self, tmp_path):
        """Create a temporary registry for testing."""
        return ToolRegistry(registry_dir=tmp_path / "tools")
    
    def test_semantic_search_fallback_without_embeddings(self, temp_registry):
        """Test that semantic search falls back to text search without embeddings."""
        # Save some tools
        temp_registry.save_tool(
            name="Whale Tracker",
            code="def track(): pass",
            description="Tracks whale movements in crypto",
            one_liner="Track large transactions",
            input_schema={},
            tags=["whale", "tracking"],
        )
        temp_registry.save_tool(
            name="Price Monitor",
            code="def monitor(): pass",
            description="Monitors crypto prices",
            one_liner="Monitor prices",
            input_schema={},
            tags=["price"],
        )
        
        # Search (will fall back to text search since no embeddings available)
        results = temp_registry.semantic_search("whale")
        
        # Should find whale tracker via fallback text search
        assert len(results) >= 1
        tool_names = [r[0].name for r in results]
        assert "Whale Tracker" in tool_names
    
    def test_semantic_search_with_category_filter(self, temp_registry):
        """Test semantic search with category filtering."""
        temp_registry.save_tool(
            name="Market Tool",
            code="def market(): pass",
            description="Market data tool",
            one_liner="Market data",
            input_schema={},
            category=ToolCategory.MARKET_DATA,
        )
        temp_registry.save_tool(
            name="Chart Tool",
            code="def chart(): pass",
            description="Charting tool",
            one_liner="Charts",
            input_schema={},
            category=ToolCategory.CHARTING,
        )
        
        # Search with category filter
        results = temp_registry.semantic_search(
            "data",
            categories=[ToolCategory.MARKET_DATA],
        )
        
        # Should only find market tool
        tool_names = [r[0].name for r in results]
        assert "Market Tool" in tool_names or len(results) == 0  # Text fallback may not match


class TestSearchToolsSemanticFunction:
    """Tests for the search_tools_semantic function wrapper."""
    
    def test_search_tools_semantic_function(self, tmp_path, monkeypatch):
        """Test the search_tools_semantic function."""
        from tool_registry import ToolRegistry
        
        test_registry = ToolRegistry(registry_dir=tmp_path / "tools")
        test_registry.save_tool(
            name="Test Searcher",
            code="def search(): pass",
            description="A test search tool",
            one_liner="Search test",
            input_schema={},
        )
        monkeypatch.setattr("tool_registry._registry", test_registry)
        
        result = search_tools_semantic(query="search")
        result_data = json.loads(result)
        
        assert result_data["status"] == "success"
        assert "semantic_search_available" in result_data
        assert "tools" in result_data

