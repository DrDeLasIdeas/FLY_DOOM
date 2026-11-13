"""Multi-scenario registry, reward shaping strategies, and factory (OCP)."""

from .factory import ScenarioFactory
from .registry import ScenarioRegistry
from .reward_shaper import (
    BasicRewardShaper,
    CombatRewardShaper,
    CorridorRewardShaper,
    NavigationRewardShaper,
    create_reward_shaper,
)

__all__ = [
    "BasicRewardShaper",
    "CombatRewardShaper",
    "CorridorRewardShaper",
    "NavigationRewardShaper",
    "ScenarioFactory",
    "ScenarioRegistry",
    "create_reward_shaper",
]
