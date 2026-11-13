"""Environment adapters (ViZDoom native + Synthetic fallback) and visual overlay."""

from .overlay import MONSTER_LABELS, EnemyOverlayDetector
from .synthetic_arena import SyntheticArenaAdapter
from .vizdoom_adapter import VIZDOOM_AVAILABLE, ViZDoomEnvironmentAdapter

__all__ = [
    "EnemyOverlayDetector",
    "MONSTER_LABELS",
    "SyntheticArenaAdapter",
    "VIZDOOM_AVAILABLE",
    "ViZDoomEnvironmentAdapter",
]
