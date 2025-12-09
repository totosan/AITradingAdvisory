"""
Dynamic Tool Registry for AITradingAdvisory

This module provides persistent storage for custom tools (code) created during
analysis sessions, with intelligent tool selection to minimize token overhead.

Key Features:
- Save any Python code as a reusable tool
- Hierarchical tool organization (tiers + categories)
- Semantic search for tool discovery using embeddings
- Two-phase tool loading (summaries first, full definition on-demand)
- Usage tracking and performance metrics

Token Optimization Strategy:
1. Tools organized into tiers: core (always), extended (intent-based), custom (on-demand)
2. Custom tools stored with short summaries for cheap discovery
3. Full tool definition loaded only when selected
4. Intent-based filtering reduces tool set before LLM call
5. Semantic search finds relevant tools using embedding similarity
"""
import json
import hashlib
import inspect
import os
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional, List, Dict, Any, Callable, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# Registry file location
REGISTRY_DIR = Path("data/tools")
REGISTRY_FILE = REGISTRY_DIR / "tool_registry.json"
EMBEDDINGS_FILE = REGISTRY_DIR / "tool_embeddings.json"

# Embedding configuration
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536  # text-embedding-3-small output dimensions


class ToolTier(Enum):
    """Tool tiers for token optimization."""
    CORE = "core"           # Always included in prompts (essential tools)
    EXTENDED = "extended"   # Included based on intent routing
    CUSTOM = "custom"       # User-created, only included when discovered


class ToolCategory(Enum):
    """Tool categories for intent-based filtering."""
    MARKET_DATA = "market_data"       # Prices, volumes, basic data
    DERIVATIVES = "derivatives"       # Futures, funding rates, OI
    TECHNICAL = "technical"           # Indicators, signals
    CHARTING = "charting"             # Chart generation
    REPORTING = "reporting"           # Report creation
    DATA_TRANSFORM = "data_transform" # Data manipulation
    EXTERNAL_API = "external_api"     # External data sources
    UTILITY = "utility"               # Helper functions
    CUSTOM = "custom"                 # User-defined


# Intent to category mapping for automatic filtering
INTENT_CATEGORY_MAP = {
    "simple_lookup": [ToolCategory.MARKET_DATA],
    "analysis": [ToolCategory.MARKET_DATA, ToolCategory.TECHNICAL, ToolCategory.DERIVATIVES],
    "chart": [ToolCategory.CHARTING, ToolCategory.MARKET_DATA, ToolCategory.TECHNICAL],
    "report": [ToolCategory.REPORTING, ToolCategory.MARKET_DATA],
    "comparison": [ToolCategory.MARKET_DATA, ToolCategory.TECHNICAL],
    "conversation": [ToolCategory.UTILITY],
}


@dataclass
class ToolSummary:
    """
    Lightweight tool summary for cheap LLM discovery.
    
    Only ~50 tokens per tool vs ~200+ for full definition.
    """
    id: str
    name: str
    one_liner: str  # Max 100 chars
    category: str
    tier: str
    usage_count: int = 0
    
    def to_prompt_line(self) -> str:
        """Format for inclusion in discovery prompt."""
        return f"- {self.name}: {self.one_liner}"


@dataclass 
class ToolDefinition:
    """Full tool definition with code and metadata."""
    id: str
    name: str
    description: str
    one_liner: str
    code: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    category: str
    tier: str
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    usage_example: str = ""
    performance_notes: str = ""
    created: str = ""
    updated: str = ""
    version: int = 1
    usage_count: int = 0
    last_used: Optional[str] = None
    
    def to_summary(self) -> ToolSummary:
        """Convert to lightweight summary."""
        return ToolSummary(
            id=self.id,
            name=self.name,
            one_liner=self.one_liner[:100],
            category=self.category,
            tier=self.tier,
            usage_count=self.usage_count,
        )
    
    def to_function_schema(self) -> Dict[str, Any]:
        """
        Convert to OpenAI function calling schema format.
        
        This is what gets sent to the LLM when the tool is selected.
        """
        return {
            "type": "function",
            "function": {
                "name": self.id,
                "description": self.description,
                "parameters": self.input_schema,
            }
        }


class EmbeddingManager:
    """
    Manages tool embeddings for semantic search.
    
    Uses Azure OpenAI's text-embedding-3-small model to create embeddings
    for tool descriptions, enabling semantic similarity search.
    
    Embeddings are cached to disk to avoid re-computation.
    """
    
    def __init__(self, embeddings_file: Optional[Path] = None):
        self.embeddings_file = embeddings_file or EMBEDDINGS_FILE
        self._embeddings_cache: Optional[Dict[str, List[float]]] = None
        self._client = None
        self._initialized = False
    
    def _load_embeddings(self) -> Dict[str, List[float]]:
        """Load embeddings from disk cache."""
        if self._embeddings_cache is not None:
            return self._embeddings_cache
        
        if self.embeddings_file.exists():
            try:
                with open(self.embeddings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._embeddings_cache = data.get("embeddings", {})
                    return self._embeddings_cache
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load embeddings: {e}")
        
        self._embeddings_cache = {}
        return self._embeddings_cache
    
    def _save_embeddings(self) -> None:
        """Save embeddings to disk cache."""
        if self._embeddings_cache is None:
            return
        
        self.embeddings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.embeddings_file, "w", encoding="utf-8") as f:
            json.dump({
                "model": EMBEDDING_MODEL,
                "dimensions": EMBEDDING_DIMENSIONS,
                "updated": datetime.now().isoformat(),
                "embeddings": self._embeddings_cache,
            }, f, indent=2)
    
    def _get_client(self):
        """Get or create the Azure OpenAI client for embeddings."""
        if self._client is not None:
            return self._client
        
        try:
            from openai import AzureOpenAI
            
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
            
            if not api_key or not endpoint:
                logger.warning("Azure OpenAI credentials not found, semantic search disabled")
                return None
            
            self._client = AzureOpenAI(
                api_key=api_key,
                azure_endpoint=endpoint,
                api_version=api_version,
            )
            self._initialized = True
            return self._client
            
        except ImportError:
            logger.warning("openai package not installed, semantic search disabled")
            return None
        except Exception as e:
            logger.warning(f"Failed to initialize Azure OpenAI client: {e}")
            return None
    
    def get_embedding(self, text: str, tool_id: Optional[str] = None) -> Optional[List[float]]:
        """
        Get embedding for a text string.
        
        If tool_id is provided, caches the embedding for reuse.
        
        Args:
            text: The text to embed
            tool_id: Optional tool ID for caching
            
        Returns:
            List of floats representing the embedding, or None if failed
        """
        # Check cache first
        if tool_id:
            embeddings = self._load_embeddings()
            if tool_id in embeddings:
                return embeddings[tool_id]
        
        client = self._get_client()
        if client is None:
            return None
        
        try:
            # Get embedding deployment name (default to model name)
            deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
            
            response = client.embeddings.create(
                input=text,
                model=deployment,
            )
            
            embedding = response.data[0].embedding
            
            # Cache if tool_id provided
            if tool_id:
                embeddings = self._load_embeddings()
                embeddings[tool_id] = embedding
                self._embeddings_cache = embeddings
                self._save_embeddings()
            
            return embedding
            
        except Exception as e:
            logger.warning(f"Failed to get embedding: {e}")
            return None
    
    def compute_tool_embedding(self, tool: ToolDefinition) -> Optional[List[float]]:
        """
        Compute and cache embedding for a tool.
        
        Creates a semantic representation combining name, description, and tags.
        """
        # Create searchable text from tool metadata
        text = f"{tool.name}. {tool.description}. Tags: {', '.join(tool.tags)}"
        return self.get_embedding(text, tool_id=tool.id)
    
    def find_similar_tools(
        self,
        query: str,
        tool_embeddings: Dict[str, List[float]],
        top_k: int = 5,
        threshold: float = 0.3,
    ) -> List[Tuple[str, float]]:
        """
        Find tools most similar to a query using cosine similarity.
        
        Args:
            query: The search query
            tool_embeddings: Dict mapping tool_id to embedding
            top_k: Number of top results to return
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of (tool_id, similarity_score) tuples, sorted by similarity
        """
        if not tool_embeddings:
            return []
        
        # Get query embedding
        query_embedding = self.get_embedding(query)
        if query_embedding is None:
            return []
        
        query_vec = np.array(query_embedding)
        
        # Compute similarities
        similarities = []
        for tool_id, tool_embedding in tool_embeddings.items():
            tool_vec = np.array(tool_embedding)
            
            # Cosine similarity
            dot_product = np.dot(query_vec, tool_vec)
            norm_product = np.linalg.norm(query_vec) * np.linalg.norm(tool_vec)
            
            if norm_product > 0:
                similarity = dot_product / norm_product
                if similarity >= threshold:
                    similarities.append((tool_id, float(similarity)))
        
        # Sort by similarity (descending) and return top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def remove_embedding(self, tool_id: str) -> None:
        """Remove a tool's embedding from the cache."""
        embeddings = self._load_embeddings()
        if tool_id in embeddings:
            del embeddings[tool_id]
            self._embeddings_cache = embeddings
            self._save_embeddings()
    
    @property
    def is_available(self) -> bool:
        """Check if semantic search is available."""
        return self._get_client() is not None


class ToolRegistry:
    """
    Manages custom tools with token-optimized discovery.
    
    Usage:
        registry = ToolRegistry()
        
        # Save a custom tool
        registry.save_tool(
            name="Whale Tracker",
            code="def track_whales(...)...",
            description="Monitors large wallet movements",
            category=ToolCategory.EXTERNAL_API,
        )
        
        # Get tools for an intent (token-optimized)
        summaries = registry.get_tool_summaries(intent_type="analysis")
        
        # Semantic search for tools
        results = registry.semantic_search("find large transactions")
        
        # Get full definition when needed
        tool = registry.get_tool("whale_tracker")
    """
    
    def __init__(self, registry_dir: Optional[Path] = None):
        self.registry_dir = registry_dir or REGISTRY_DIR
        self.registry_file = self.registry_dir / "tool_registry.json"
        self._cache: Optional[Dict[str, Any]] = None
        self._embedding_manager: Optional[EmbeddingManager] = None
    
    @property
    def embedding_manager(self) -> EmbeddingManager:
        """Lazy initialization of embedding manager."""
        if self._embedding_manager is None:
            embeddings_file = self.registry_dir / "tool_embeddings.json"
            self._embedding_manager = EmbeddingManager(embeddings_file)
        return self._embedding_manager
    
    def _ensure_registry_exists(self) -> Dict[str, Any]:
        """Ensure the registry directory and file exist."""
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        
        if self._cache is not None:
            return self._cache
        
        if self.registry_file.exists():
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                    return self._cache
            except (json.JSONDecodeError, IOError):
                pass
        
        # Initialize empty registry
        self._cache = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "tools": {},
            "category_index": {},  # category -> [tool_ids] for fast lookup
            "tag_index": {},       # tag -> [tool_ids] for search
        }
        self._save_registry()
        return self._cache
    
    def _save_registry(self) -> None:
        """Save registry to disk."""
        if self._cache is None:
            return
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self._cache["last_updated"] = datetime.now().isoformat()
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, indent=2)
    
    def _generate_tool_id(self, name: str) -> str:
        """Generate a unique ID for a tool based on its name."""
        clean_name = name.lower().replace(" ", "_")
        clean_name = "".join(c for c in clean_name if c.isalnum() or c == "_")
        return clean_name
    
    def _update_indexes(self, tool_id: str, tool: Dict[str, Any], remove: bool = False) -> None:
        """Update category and tag indexes."""
        registry = self._ensure_registry_exists()
        
        # Update category index
        category = tool.get("category", "custom")
        if category not in registry["category_index"]:
            registry["category_index"][category] = []
        
        if remove:
            if tool_id in registry["category_index"][category]:
                registry["category_index"][category].remove(tool_id)
        else:
            if tool_id not in registry["category_index"][category]:
                registry["category_index"][category].append(tool_id)
        
        # Update tag index
        for tag in tool.get("tags", []):
            if tag not in registry["tag_index"]:
                registry["tag_index"][tag] = []
            
            if remove:
                if tool_id in registry["tag_index"][tag]:
                    registry["tag_index"][tag].remove(tool_id)
            else:
                if tool_id not in registry["tag_index"][tag]:
                    registry["tag_index"][tag].append(tool_id)
    
    def save_tool(
        self,
        name: str,
        code: str,
        description: str,
        one_liner: str,
        input_schema: Dict[str, Any],
        output_schema: Optional[Dict[str, Any]] = None,
        category: ToolCategory = ToolCategory.CUSTOM,
        tier: ToolTier = ToolTier.CUSTOM,
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        usage_example: str = "",
        performance_notes: str = "",
    ) -> Tuple[str, ToolDefinition]:
        """
        Save a custom tool to the registry.
        
        Args:
            name: Human-readable tool name
            code: Python function code
            description: Full description for LLM
            one_liner: Short description (<100 chars) for discovery
            input_schema: JSON schema for function parameters
            output_schema: JSON schema for return value
            category: Tool category for filtering
            tier: Tool tier for inclusion strategy
            tags: Searchable tags
            dependencies: Required Python packages
            usage_example: Example code
            performance_notes: Performance characteristics
            
        Returns:
            Tuple of (tool_id, ToolDefinition)
        """
        registry = self._ensure_registry_exists()
        tool_id = self._generate_tool_id(name)
        
        is_update = tool_id in registry["tools"]
        existing = registry["tools"].get(tool_id, {})
        
        tool_data = {
            "id": tool_id,
            "name": name,
            "description": description,
            "one_liner": one_liner[:100],
            "code": code,
            "input_schema": input_schema,
            "output_schema": output_schema or {"type": "string"},
            "category": category.value if isinstance(category, ToolCategory) else category,
            "tier": tier.value if isinstance(tier, ToolTier) else tier,
            "tags": tags or [],
            "dependencies": dependencies or [],
            "usage_example": usage_example,
            "performance_notes": performance_notes,
            "created": existing.get("created", datetime.now().isoformat()),
            "updated": datetime.now().isoformat(),
            "version": existing.get("version", 0) + 1,
            "usage_count": existing.get("usage_count", 0),
            "last_used": existing.get("last_used"),
        }
        
        # Save to registry
        registry["tools"][tool_id] = tool_data
        self._update_indexes(tool_id, tool_data)
        self._save_registry()
        
        # Also save code to separate file for inspection
        code_file = self.registry_dir / f"{tool_id}.py"
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(f'"""\n{name}\n\n{description}\n\nInput Schema: {json.dumps(input_schema, indent=2)}\n\nUsage:\n{usage_example}\n"""\n\n')
            f.write(code)
        
        # Compute and cache embedding for semantic search
        tool_def = ToolDefinition(**tool_data)
        try:
            self.embedding_manager.compute_tool_embedding(tool_def)
        except Exception as e:
            logger.warning(f"Failed to compute embedding for tool {tool_id}: {e}")
        
        return tool_id, tool_def
    
    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        """Get full tool definition by ID."""
        registry = self._ensure_registry_exists()
        
        if tool_id not in registry["tools"]:
            # Try partial match
            matches = [k for k in registry["tools"].keys() if tool_id.lower() in k.lower()]
            if len(matches) == 1:
                tool_id = matches[0]
            else:
                return None
        
        tool_data = registry["tools"][tool_id]
        
        # Increment usage count
        tool_data["usage_count"] = tool_data.get("usage_count", 0) + 1
        tool_data["last_used"] = datetime.now().isoformat()
        self._save_registry()
        
        return ToolDefinition(**tool_data)
    
    def get_tool_summaries(
        self,
        intent_type: Optional[str] = None,
        categories: Optional[List[ToolCategory]] = None,
        tier: Optional[ToolTier] = None,
        search: Optional[str] = None,
        limit: int = 20,
    ) -> List[ToolSummary]:
        """
        Get lightweight tool summaries for discovery.
        
        This is the token-optimized entry point. Returns only essential
        info (~50 tokens per tool) for LLM to decide which tools to use.
        
        Args:
            intent_type: Filter by intent (uses INTENT_CATEGORY_MAP)
            categories: Filter by specific categories
            tier: Filter by tier
            search: Text search in name/tags
            limit: Max tools to return
            
        Returns:
            List of ToolSummary objects
        """
        registry = self._ensure_registry_exists()
        tools = registry["tools"]
        
        # Determine categories from intent
        if intent_type and not categories:
            categories = INTENT_CATEGORY_MAP.get(intent_type, [])
        
        results = []
        for tool_id, tool_data in tools.items():
            # Category filter
            if categories:
                tool_cat = tool_data.get("category", "custom")
                if not any(cat.value == tool_cat for cat in categories):
                    continue
            
            # Tier filter
            if tier:
                if tool_data.get("tier") != tier.value:
                    continue
            
            # Search filter
            if search:
                search_lower = search.lower()
                searchable = f"{tool_data.get('name', '')} {' '.join(tool_data.get('tags', []))}".lower()
                if search_lower not in searchable:
                    continue
            
            results.append(ToolSummary(
                id=tool_id,
                name=tool_data.get("name", tool_id),
                one_liner=tool_data.get("one_liner", "")[:100],
                category=tool_data.get("category", "custom"),
                tier=tool_data.get("tier", "custom"),
                usage_count=tool_data.get("usage_count", 0),
            ))
        
        # Sort by usage count (most used first)
        results.sort(key=lambda x: x.usage_count, reverse=True)
        
        return results[:limit]
    
    def get_tools_for_intent(
        self,
        intent_type: str,
        include_custom: bool = True,
        max_custom: int = 5,
    ) -> Tuple[List[ToolDefinition], List[ToolSummary]]:
        """
        Get tools optimized for an intent.
        
        Returns two lists:
        1. Full definitions for core/extended tools (included in prompt)
        2. Summaries for custom tools (for discovery, loaded on-demand)
        
        This minimizes tokens while keeping custom tools discoverable.
        
        Args:
            intent_type: The detected intent type
            include_custom: Whether to include custom tool summaries
            max_custom: Max custom tools to include in summaries
            
        Returns:
            Tuple of (full_definitions, custom_summaries)
        """
        registry = self._ensure_registry_exists()
        categories = INTENT_CATEGORY_MAP.get(intent_type, [])
        
        full_defs = []
        custom_summaries = []
        
        for tool_id, tool_data in registry["tools"].items():
            tool_tier = tool_data.get("tier", "custom")
            tool_cat = tool_data.get("category", "custom")
            
            # Check category match
            cat_match = not categories or any(cat.value == tool_cat for cat in categories)
            
            if tool_tier == ToolTier.CORE.value:
                # Core tools always included with full definition
                full_defs.append(ToolDefinition(**tool_data))
            elif tool_tier == ToolTier.EXTENDED.value and cat_match:
                # Extended tools included if category matches
                full_defs.append(ToolDefinition(**tool_data))
            elif tool_tier == ToolTier.CUSTOM.value and include_custom and cat_match:
                # Custom tools only as summaries
                if len(custom_summaries) < max_custom:
                    custom_summaries.append(ToolSummary(
                        id=tool_id,
                        name=tool_data.get("name", tool_id),
                        one_liner=tool_data.get("one_liner", "")[:100],
                        category=tool_cat,
                        tier=tool_tier,
                        usage_count=tool_data.get("usage_count", 0),
                    ))
        
        # Sort custom by usage
        custom_summaries.sort(key=lambda x: x.usage_count, reverse=True)
        
        return full_defs, custom_summaries
    
    def delete_tool(self, tool_id: str) -> bool:
        """Delete a tool from the registry."""
        registry = self._ensure_registry_exists()
        
        if tool_id not in registry["tools"]:
            return False
        
        tool_data = registry["tools"].pop(tool_id)
        self._update_indexes(tool_id, tool_data, remove=True)
        self._save_registry()
        
        # Remove code file
        code_file = self.registry_dir / f"{tool_id}.py"
        if code_file.exists():
            code_file.unlink()
        
        # Remove embedding
        try:
            self.embedding_manager.remove_embedding(tool_id)
        except Exception as e:
            logger.warning(f"Failed to remove embedding for tool {tool_id}: {e}")
        
        return True
    
    def semantic_search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.3,
        categories: Optional[List[ToolCategory]] = None,
    ) -> List[Tuple[ToolSummary, float]]:
        """
        Find tools semantically similar to a query using embeddings.
        
        This is the most intelligent way to discover relevant tools.
        Uses text-embedding-3-small to encode the query and compare
        against pre-computed tool embeddings.
        
        Args:
            query: Natural language description of what you're looking for
            top_k: Number of top results to return
            threshold: Minimum similarity score (0-1)
            categories: Optional category filter
            
        Returns:
            List of (ToolSummary, similarity_score) tuples, sorted by relevance
        """
        if not self.embedding_manager.is_available:
            logger.info("Semantic search not available, falling back to text search")
            # Fallback to text search
            summaries = self.get_tool_summaries(search=query, categories=categories, limit=top_k)
            return [(s, 1.0) for s in summaries]
        
        registry = self._ensure_registry_exists()
        tools = registry["tools"]
        
        # Get embeddings for all tools (from cache or compute)
        tool_embeddings = {}
        for tool_id, tool_data in tools.items():
            # Apply category filter
            if categories:
                tool_cat = tool_data.get("category", "custom")
                if not any(cat.value == tool_cat for cat in categories):
                    continue
            
            # Get or compute embedding
            embedding = self.embedding_manager._load_embeddings().get(tool_id)
            if embedding is None:
                # Compute on the fly
                tool_def = ToolDefinition(**tool_data)
                embedding = self.embedding_manager.compute_tool_embedding(tool_def)
            
            if embedding:
                tool_embeddings[tool_id] = embedding
        
        # Find similar tools
        similar = self.embedding_manager.find_similar_tools(
            query=query,
            tool_embeddings=tool_embeddings,
            top_k=top_k,
            threshold=threshold,
        )
        
        # Convert to ToolSummary with scores
        results = []
        for tool_id, score in similar:
            if tool_id in tools:
                tool_data = tools[tool_id]
                summary = ToolSummary(
                    id=tool_id,
                    name=tool_data.get("name", tool_id),
                    one_liner=tool_data.get("one_liner", "")[:100],
                    category=tool_data.get("category", "custom"),
                    tier=tool_data.get("tier", "custom"),
                    usage_count=tool_data.get("usage_count", 0),
                )
                results.append((summary, score))
        
        return results
    
    def get_discovery_prompt(
        self,
        intent_type: Optional[str] = None,
        max_tools: int = 10,
    ) -> str:
        """
        Generate a token-efficient discovery prompt for custom tools.
        
        This is for the LLM to decide if any custom tools are relevant.
        Uses only ~50 tokens per tool.
        
        Example output:
            Available custom tools:
            - whale_tracker: Monitors large wallet movements for specified tokens
            - correlation_matrix: Calculates rolling correlation between assets
            - sentiment_scorer: Analyzes social media sentiment for crypto assets
            
            To use a custom tool, specify its name and I'll load the full definition.
        """
        summaries = self.get_tool_summaries(
            intent_type=intent_type,
            tier=ToolTier.CUSTOM,
            limit=max_tools,
        )
        
        if not summaries:
            return ""
        
        lines = ["Available custom tools:"]
        for s in summaries:
            lines.append(s.to_prompt_line())
        lines.append("")
        lines.append("To use a custom tool, specify its name and I'll load the full definition.")
        
        return "\n".join(lines)
    
    def execute_tool(
        self,
        tool_id: str,
        parameters: Dict[str, Any],
    ) -> str:
        """
        Execute a tool with given parameters.
        
        Loads the tool code and executes it safely.
        
        Args:
            tool_id: The tool to execute
            parameters: Input parameters as dict
            
        Returns:
            JSON string with result or error
        """
        tool = self.get_tool(tool_id)
        if not tool:
            return json.dumps({
                "status": "error",
                "message": f"Tool '{tool_id}' not found"
            })
        
        try:
            # Create execution namespace
            import pandas as pd
            import numpy as np
            
            namespace = {
                "pd": pd,
                "np": np,
                "datetime": datetime,
                "json": json,
                **parameters,
            }
            
            # Execute tool code
            exec(tool.code, namespace)
            
            # Find the main function (first defined function)
            for name, obj in namespace.items():
                if callable(obj) and not name.startswith("_") and name not in ["pd", "np", "datetime", "json"]:
                    result = obj(**parameters)
                    return json.dumps({
                        "status": "success",
                        "result": result if isinstance(result, (str, dict, list, int, float, bool)) else str(result)
                    })
            
            return json.dumps({
                "status": "error",
                "message": "No callable function found in tool code"
            })
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Execution failed: {str(e)}"
            })


# ═══════════════════════════════════════════════════════════════════════════════
# Tool Functions for Agent Integration
# ═══════════════════════════════════════════════════════════════════════════════

# Global registry instance
_registry: Optional[ToolRegistry] = None


def _get_registry() -> ToolRegistry:
    """Get or create the global registry instance."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def save_custom_tool(
    name: Annotated[str, "Name of the tool (e.g., 'Whale Tracker', 'Correlation Matrix')"],
    code: Annotated[str, "The Python code implementing the tool function"],
    description: Annotated[str, "Full description of what the tool does and how it works"],
    one_liner: Annotated[str, "Very short description (max 100 chars) for quick discovery"],
    input_schema: Annotated[str, "JSON schema describing the input parameters"],
    category: Annotated[str, "Category: 'market_data', 'derivatives', 'technical', 'charting', 'reporting', 'data_transform', 'external_api', 'utility', 'custom'"] = "custom",
    tags: Annotated[Optional[str], "Comma-separated tags for searchability"] = None,
    usage_example: Annotated[str, "Example of how to use the tool"] = "",
) -> str:
    """
    Save a custom tool to the persistent registry for reuse in future conversations.
    
    The tool will be available for discovery and execution in all future sessions.
    To minimize token overhead, only a short summary is included in prompts until
    the tool is explicitly requested.
    
    Args:
        name: Human-readable tool name
        code: Python function code (must define a callable function)
        description: Full description for when tool is loaded
        one_liner: Short summary for discovery (keeps token count low)
        input_schema: JSON schema for parameters
        category: Tool category for intent-based filtering
        tags: Searchable tags
        usage_example: How to use the tool
        
    Returns:
        JSON string with status and tool ID
    """
    try:
        registry = _get_registry()
        
        # Parse input schema
        try:
            schema = json.loads(input_schema) if isinstance(input_schema, str) else input_schema
        except json.JSONDecodeError:
            schema = {"type": "object", "properties": {}, "description": input_schema}
        
        # Parse tags
        tags_list = [t.strip() for t in tags.split(",")] if tags else []
        
        # Map category string to enum
        cat_map = {c.value: c for c in ToolCategory}
        tool_category = cat_map.get(category, ToolCategory.CUSTOM)
        
        tool_id, tool_def = registry.save_tool(
            name=name,
            code=code,
            description=description,
            one_liner=one_liner,
            input_schema=schema,
            category=tool_category,
            tags=tags_list,
            usage_example=usage_example,
        )
        
        return json.dumps({
            "status": "success",
            "tool_id": tool_id,
            "name": name,
            "category": category,
            "message": f"Tool '{name}' saved successfully. It will be available for discovery in future conversations.",
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to save tool: {str(e)}",
        })


def list_custom_tools(
    category: Annotated[Optional[str], "Filter by category, or None for all"] = None,
    search: Annotated[Optional[str], "Search term to filter by name or tags"] = None,
) -> str:
    """
    List available custom tools with their summaries.
    
    Returns lightweight summaries to minimize token usage. Use get_custom_tool()
    to retrieve the full definition when needed.
    
    Args:
        category: Optional category filter
        search: Optional search term
        
    Returns:
        JSON string with list of tool summaries
    """
    try:
        registry = _get_registry()
        
        categories = None
        if category:
            cat_map = {c.value: c for c in ToolCategory}
            if category in cat_map:
                categories = [cat_map[category]]
        
        summaries = registry.get_tool_summaries(
            categories=categories,
            search=search,
        )
        
        return json.dumps({
            "status": "success",
            "total_tools": len(summaries),
            "tools": [asdict(s) for s in summaries],
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to list tools: {str(e)}",
        })


def get_custom_tool(
    tool_id: Annotated[str, "The tool ID to retrieve"],
) -> str:
    """
    Get the full definition of a custom tool.
    
    Use this after discovering a tool via list_custom_tools() to get
    the complete code, parameters, and usage information.
    
    Args:
        tool_id: The ID of the tool to retrieve
        
    Returns:
        JSON string with full tool definition including code
    """
    try:
        registry = _get_registry()
        tool = registry.get_tool(tool_id)
        
        if not tool:
            return json.dumps({
                "status": "error",
                "message": f"Tool '{tool_id}' not found. Use list_custom_tools() to see available tools.",
            })
        
        return json.dumps({
            "status": "success",
            "tool": asdict(tool),
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to get tool: {str(e)}",
        })


def execute_custom_tool(
    tool_id: Annotated[str, "The tool ID to execute"],
    parameters: Annotated[str, "JSON object of input parameters"],
) -> str:
    """
    Execute a custom tool with the given parameters.
    
    Loads the tool code and executes it with the provided inputs.
    
    Args:
        tool_id: The ID of the tool to execute
        parameters: JSON object of input parameters
        
    Returns:
        JSON string with execution result
    """
    try:
        registry = _get_registry()
        
        params = json.loads(parameters) if isinstance(parameters, str) else parameters
        return registry.execute_tool(tool_id, params)
        
    except json.JSONDecodeError:
        return json.dumps({
            "status": "error",
            "message": "Invalid JSON in parameters",
        })
    except Exception as e:
        return json.dumps({
            "status": "error", 
            "message": f"Execution failed: {str(e)}",
        })


def delete_custom_tool(
    tool_id: Annotated[str, "The tool ID to delete"],
    confirm: Annotated[bool, "Must be True to confirm deletion"] = False,
) -> str:
    """
    Delete a custom tool from the registry.
    
    Args:
        tool_id: The ID of the tool to delete
        confirm: Must be True to confirm deletion
        
    Returns:
        JSON string with deletion status
    """
    try:
        if not confirm:
            return json.dumps({
                "status": "error",
                "message": "Deletion not confirmed. Set confirm=True to delete.",
            })
        
        registry = _get_registry()
        success = registry.delete_tool(tool_id)
        
        if success:
            return json.dumps({
                "status": "success",
                "message": f"Tool '{tool_id}' deleted successfully.",
            }, indent=2)
        else:
            return json.dumps({
                "status": "error",
                "message": f"Tool '{tool_id}' not found.",
            })
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to delete tool: {str(e)}",
        })


def search_tools_semantic(
    query: Annotated[str, "Natural language description of the tool you're looking for"],
    top_k: Annotated[int, "Number of top results to return"] = 5,
    category: Annotated[Optional[str], "Filter by category, or None for all"] = None,
) -> str:
    """
    Search for tools using semantic similarity (embeddings).
    
    This is the most intelligent way to find relevant tools. It uses
    text-embedding-3-small to understand the meaning of your query
    and find tools that match semantically, even if they don't contain
    the exact words you used.
    
    Examples:
        - "track large crypto transactions" → finds "whale_tracker"
        - "analyze price movements" → finds technical analysis tools
        - "fetch market sentiment" → finds sentiment analysis tools
    
    Args:
        query: What you're looking for in natural language
        top_k: How many results to return
        category: Optional category filter
        
    Returns:
        JSON string with matching tools and similarity scores
    """
    try:
        registry = _get_registry()
        
        categories = None
        if category:
            cat_map = {c.value: c for c in ToolCategory}
            if category in cat_map:
                categories = [cat_map[category]]
        
        results = registry.semantic_search(
            query=query,
            top_k=top_k,
            categories=categories,
        )
        
        return json.dumps({
            "status": "success",
            "query": query,
            "semantic_search_available": registry.embedding_manager.is_available,
            "total_matches": len(results),
            "tools": [
                {
                    **asdict(summary),
                    "similarity_score": round(score, 3),
                }
                for summary, score in results
            ],
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Semantic search failed: {str(e)}",
        })

