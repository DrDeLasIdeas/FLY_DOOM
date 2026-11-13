"""Multi-scenario registry, reward shaping strategies, and factory (OCP)."""

from .factory import ScenarioFactory
from .registry import ScenarioRegistry
from . reward_shaper import (
    AssaultRewardShaper,
    BasicRewardShaper,
    CombatRewardShaper,
    CorridorRewardShaper,
    DodgeRewardShaper,
    NavigationRewardShaper,
    create_reward_shaper,
)

__all__ = [
    "AssaultRewardShaper",
    "BasicRewardShaper",
    "CombatRewardShaper",
    "CorridorRewardShaper",
    "DodgeRewardShaper",
    "NavigationRewardShaper",
    "ScenarioFactory",
    "ScenarioRegistry",
    "create_reward_shaper",
]
