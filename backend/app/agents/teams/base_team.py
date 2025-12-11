"""
Base Team Configuration for AITradingAdvisory Agent Teams.

Provides common infrastructure for specialized agent teams.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from intent_router import StrategyType


@dataclass
class TeamConfig:
    """
    Configuration for an agent team.
    
    Attributes:
        name: Team display name
        description: Team description for logging
        feedback_strategy: Strategy type for feedback isolation (Phase 7)
        agents: List of agent names in the team
        tools: List of tool functions available to the team
        system_prompt_additions: Additional system prompt context
        max_turns: Maximum conversation turns for the team
        focus_area: Primary focus area description
    """
    name: str
    description: str
    feedback_strategy: StrategyType
    agents: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    system_prompt_additions: str = ""
    max_turns: int = 10
    focus_area: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "feedback_strategy": self.feedback_strategy.value,
            "agents": self.agents,
            "tools": self.tools,
            "max_turns": self.max_turns,
            "focus_area": self.focus_area,
        }


class BaseTeam:
    """
    Base class for specialized agent teams.
    
    Each team is optimized for a specific market phase and uses
    a dedicated feedback_strategy for isolated learning (Phase 7).
    """
    
    # Override in subclasses
    config: TeamConfig = None
    
    def __init__(self, model_client=None, user_id: Optional[str] = None):
        """
        Initialize the team.
        
        Args:
            model_client: LLM client for agent creation
            user_id: User ID for user-scoped feedback
        """
        self.model_client = model_client
        self.user_id = user_id
        self._agents = []
        self._tools = []
    
    @classmethod
    def get_feedback_strategy(cls) -> StrategyType:
        """Get the feedback strategy for this team."""
        return cls.config.feedback_strategy if cls.config else StrategyType.UNKNOWN
    
    @classmethod
    def get_tool_names(cls) -> List[str]:
        """Get the list of tool names for this team."""
        return cls.config.tools if cls.config else []
    
    @classmethod
    def get_system_prompt_additions(cls) -> str:
        """Get additional system prompt context for this team."""
        return cls.config.system_prompt_additions if cls.config else ""
    
    def get_tools(self) -> List[Callable]:
        """
        Get the actual tool functions for this team.
        
        Subclasses should override to return specific tool implementations.
        """
        return self._tools
    
    def get_feedback_context(self) -> str:
        """
        Get feedback context from the Learning System (Phase 7).
        
        This injects historical performance feedback into agent prompts.
        """
        try:
            from learning_system import get_feedback_context
            return get_feedback_context(
                strategy_type=self.get_feedback_strategy(),
                user_id=self.user_id,
            )
        except Exception:
            return ""
    
    def build_system_prompt(self, base_prompt: str) -> str:
        """
        Build complete system prompt with team-specific additions and feedback.
        
        Args:
            base_prompt: The base system prompt for the agent
            
        Returns:
            Enhanced system prompt with team context and feedback
        """
        additions = self.get_system_prompt_additions()
        feedback = self.get_feedback_context()
        
        parts = [base_prompt]
        
        if additions:
            parts.append(f"\n\n{additions}")
        
        if feedback:
            parts.append(f"\n\n📊 PERFORMANCE FEEDBACK:\n{feedback}")
        
        return "".join(parts)
