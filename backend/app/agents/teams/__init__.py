"""
Agent Teams Module for AITradingAdvisory.

Contains specialized agent teams for different market phases:
- RangeTeam: Optimized for range/consolidation markets
- BreakoutTeam: Optimized for breakout trading
- TrendTeam: Optimized for trend-following
- ReversalTeam: Optimized for reversal detection
"""

from .range_team import RangeTeam, create_range_team
from .breakout_team import BreakoutTeam, create_breakout_team
from .base_team import BaseTeam, TeamConfig

__all__ = [
    "BaseTeam",
    "TeamConfig",
    "RangeTeam",
    "BreakoutTeam",
    "create_range_team",
    "create_breakout_team",
]
