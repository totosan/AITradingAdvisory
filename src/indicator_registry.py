"""
Custom Indicator Registry for MagenticOne

This module provides persistent storage for custom indicators created during
analysis sessions. Indicators are saved to disk and can be reused across
sessions and made available to all agents.

Features:
- Save custom indicator code with metadata
- List available indicators with descriptions
- Load indicator code for reuse
- Categorize and tag indicators
- Track usage and performance notes
"""
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional, List, Dict, Any


# Registry file location
REGISTRY_DIR = Path("data/indicators")
REGISTRY_FILE = REGISTRY_DIR / "indicator_registry.json"


def _ensure_registry_exists() -> Dict[str, Any]:
    """Ensure the registry directory and file exist, return current registry."""
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    
    if REGISTRY_FILE.exists():
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    # Initialize empty registry
    registry = {
        "version": "1.0",
        "created": datetime.now().isoformat(),
        "indicators": {}
    }
    _save_registry(registry)
    return registry


def _save_registry(registry: Dict[str, Any]) -> None:
    """Save registry to disk."""
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    registry["last_updated"] = datetime.now().isoformat()
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)


def _generate_indicator_id(name: str) -> str:
    """Generate a unique ID for an indicator based on its name."""
    # Clean name and create ID
    clean_name = name.lower().replace(" ", "_")
    clean_name = "".join(c for c in clean_name if c.isalnum() or c == "_")
    return clean_name


def save_custom_indicator(
    name: Annotated[str, "Name of the indicator (e.g., 'Funding Rate Momentum', 'Volume Weighted RSI')"],
    code: Annotated[str, "The Python code implementing the indicator function"],
    description: Annotated[str, "Description of what the indicator measures and how it works"],
    parameters: Annotated[str, "JSON string describing the parameters (e.g., '{\"period\": 14, \"threshold\": 0.5}')"],
    usage_example: Annotated[str, "Example of how to use the indicator with sample code"],
    category: Annotated[str, "Category: 'momentum', 'trend', 'volatility', 'volume', 'sentiment', 'composite', 'other'"] = "other",
    tags: Annotated[Optional[str], "Comma-separated tags for searchability (e.g., 'rsi,funding,futures')"] = None,
    performance_notes: Annotated[Optional[str], "Notes on backtesting results or known performance characteristics"] = None,
) -> str:
    """
    Save a custom indicator to the persistent registry.
    
    The indicator will be available for reuse in future sessions and
    accessible to all agents in the system.
    
    Args:
        name: Human-readable indicator name
        code: Python function code (must be a complete, executable function)
        description: What the indicator does
        parameters: JSON string of default parameters
        usage_example: How to use the indicator
        category: Type of indicator
        tags: Searchable tags
        performance_notes: Backtesting results or notes
        
    Returns:
        JSON string with status and indicator ID
    """
    try:
        registry = _ensure_registry_exists()
        indicator_id = _generate_indicator_id(name)
        
        # Parse parameters
        try:
            params_dict = json.loads(parameters) if parameters else {}
        except json.JSONDecodeError:
            params_dict = {"raw": parameters}
        
        # Parse tags
        tags_list = [t.strip() for t in tags.split(",")] if tags else []
        
        # Check if updating existing indicator
        is_update = indicator_id in registry["indicators"]
        
        # Create indicator entry
        indicator = {
            "id": indicator_id,
            "name": name,
            "description": description,
            "category": category,
            "tags": tags_list,
            "parameters": params_dict,
            "code": code,
            "usage_example": usage_example,
            "performance_notes": performance_notes,
            "created": datetime.now().isoformat() if not is_update else registry["indicators"].get(indicator_id, {}).get("created", datetime.now().isoformat()),
            "updated": datetime.now().isoformat(),
            "version": registry["indicators"].get(indicator_id, {}).get("version", 0) + 1 if is_update else 1,
            "usage_count": registry["indicators"].get(indicator_id, {}).get("usage_count", 0),
        }
        
        # Save to registry
        registry["indicators"][indicator_id] = indicator
        _save_registry(registry)
        
        # Also save the code to a separate Python file for easy importing
        code_file = REGISTRY_DIR / f"{indicator_id}.py"
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(f'"""\n{name}\n\n{description}\n\nParameters: {json.dumps(params_dict, indent=2)}\n\nUsage:\n{usage_example}\n"""\n\n')
            f.write(code)
        
        return json.dumps({
            "status": "success",
            "action": "updated" if is_update else "created",
            "indicator_id": indicator_id,
            "name": name,
            "category": category,
            "code_file": str(code_file),
            "message": f"Indicator '{name}' saved successfully. Use list_custom_indicators() to see all available indicators.",
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to save indicator: {str(e)}",
        })


def list_custom_indicators(
    category: Annotated[Optional[str], "Filter by category: 'momentum', 'trend', 'volatility', 'volume', 'sentiment', 'composite', 'other', or None for all"] = None,
    search: Annotated[Optional[str], "Search term to filter indicators by name, description, or tags"] = None,
) -> str:
    """
    List all available custom indicators in the registry.
    
    Returns a summary of each indicator including name, description,
    category, and usage count. Use get_custom_indicator() to retrieve
    the full code for a specific indicator.
    
    Args:
        category: Optional category filter
        search: Optional search term
        
    Returns:
        JSON string with list of indicators
    """
    try:
        registry = _ensure_registry_exists()
        indicators = registry.get("indicators", {})
        
        results = []
        for ind_id, ind in indicators.items():
            # Apply category filter
            if category and ind.get("category") != category:
                continue
            
            # Apply search filter
            if search:
                search_lower = search.lower()
                searchable = f"{ind.get('name', '')} {ind.get('description', '')} {' '.join(ind.get('tags', []))}".lower()
                if search_lower not in searchable:
                    continue
            
            results.append({
                "id": ind_id,
                "name": ind.get("name"),
                "description": ind.get("description", "")[:200] + "..." if len(ind.get("description", "")) > 200 else ind.get("description", ""),
                "category": ind.get("category"),
                "tags": ind.get("tags", []),
                "parameters": ind.get("parameters", {}),
                "version": ind.get("version", 1),
                "usage_count": ind.get("usage_count", 0),
                "updated": ind.get("updated"),
            })
        
        # Sort by usage count (most used first)
        results.sort(key=lambda x: x.get("usage_count", 0), reverse=True)
        
        return json.dumps({
            "status": "success",
            "total_indicators": len(registry.get("indicators", {})),
            "matching_indicators": len(results),
            "filter": {"category": category, "search": search},
            "indicators": results,
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to list indicators: {str(e)}",
        })


def get_custom_indicator(
    indicator_id: Annotated[str, "The indicator ID (from list_custom_indicators) to retrieve"],
) -> str:
    """
    Get the full details and code for a specific custom indicator.
    
    Retrieves the complete indicator including code, parameters,
    usage examples, and performance notes. Also increments the
    usage counter.
    
    Args:
        indicator_id: The ID of the indicator to retrieve
        
    Returns:
        JSON string with full indicator details including code
    """
    try:
        registry = _ensure_registry_exists()
        indicators = registry.get("indicators", {})
        
        if indicator_id not in indicators:
            # Try to find by partial match
            matches = [k for k in indicators.keys() if indicator_id.lower() in k.lower()]
            if matches:
                return json.dumps({
                    "status": "error",
                    "message": f"Indicator '{indicator_id}' not found. Did you mean: {', '.join(matches)}?",
                })
            return json.dumps({
                "status": "error",
                "message": f"Indicator '{indicator_id}' not found. Use list_custom_indicators() to see available indicators.",
            })
        
        indicator = indicators[indicator_id]
        
        # Increment usage count
        indicator["usage_count"] = indicator.get("usage_count", 0) + 1
        indicator["last_used"] = datetime.now().isoformat()
        registry["indicators"][indicator_id] = indicator
        _save_registry(registry)
        
        return json.dumps({
            "status": "success",
            "indicator": indicator,
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to get indicator: {str(e)}",
        })


def delete_custom_indicator(
    indicator_id: Annotated[str, "The indicator ID to delete"],
    confirm: Annotated[bool, "Must be True to confirm deletion"] = False,
) -> str:
    """
    Delete a custom indicator from the registry.
    
    Args:
        indicator_id: The ID of the indicator to delete
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
        
        registry = _ensure_registry_exists()
        indicators = registry.get("indicators", {})
        
        if indicator_id not in indicators:
            return json.dumps({
                "status": "error",
                "message": f"Indicator '{indicator_id}' not found.",
            })
        
        # Remove from registry
        deleted = indicators.pop(indicator_id)
        registry["indicators"] = indicators
        _save_registry(registry)
        
        # Remove code file if exists
        code_file = REGISTRY_DIR / f"{indicator_id}.py"
        if code_file.exists():
            code_file.unlink()
        
        return json.dumps({
            "status": "success",
            "message": f"Indicator '{deleted.get('name')}' deleted successfully.",
            "deleted_id": indicator_id,
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to delete indicator: {str(e)}",
        })


def get_indicator_code_for_execution(
    indicator_id: Annotated[str, "The indicator ID to get executable code for"],
) -> str:
    """
    Get just the executable Python code for an indicator.
    
    Returns the raw Python code that can be directly executed.
    Useful for the Executor agent to run the indicator.
    
    Args:
        indicator_id: The ID of the indicator
        
    Returns:
        The Python code as a string, or error message
    """
    try:
        registry = _ensure_registry_exists()
        indicators = registry.get("indicators", {})
        
        if indicator_id not in indicators:
            return f"# Error: Indicator '{indicator_id}' not found"
        
        indicator = indicators[indicator_id]
        
        # Return code with imports and docstring
        code = f'''"""
{indicator.get("name", indicator_id)}

{indicator.get("description", "")}

Parameters: {json.dumps(indicator.get("parameters", {}), indent=2)}
"""

# Required imports
import pandas as pd
import numpy as np
from datetime import datetime

{indicator.get("code", "# No code available")}

# Usage example:
# {indicator.get("usage_example", "See indicator documentation").replace(chr(10), chr(10) + "# ")}
'''
        return code
        
    except Exception as e:
        return f"# Error loading indicator: {str(e)}"
