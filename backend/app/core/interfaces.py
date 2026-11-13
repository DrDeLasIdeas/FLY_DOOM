"""SOLID interfaces (ABC / Protocols) and typed DTOs for NeuroDoom OS.

Applies:
- Interface Segregation Principle (ISP): separate contracts for visual
  preprocessing, environment stepping, reward shaping, RL policy learning,
  biophysical SNN simulation, and asynchronous neuromodulation.
- Dependency Inversion Principle (DIP): orchestrators and trainers depend on
  these abstractions rather than concrete ViZDoom, PyTorch, or HTTP classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import numpy as np


@dataclass(frozen=True)
class ActionSpec:
    """Declarative mapping between a discrete action index and ViZDoom buttons."""

    name: str
    label: str
    buttons: list[int]


@dataclass(frozen=True)
class ScenarioConfig:
    """Declarative configuration for a ViZDoom scenario (.cfg / .wad)."""

    id: str
    name: str
    description: str
    cfg_file: str
    buttons: list[str]
    actions: list[ActionSpec]
    game_variables: list[str] = field(default_factory=lambda: ["AMMO2", "HEALTH"])
    episode_timeout: int = 900
    default_skill: int = 3
    ammo_max: float = 26.0
    reward_shaper: str = "combat"
    is_combat: bool = True
    custom_cfg_path: str | None = None
    custom_wad_path: str | None = None


@dataclass
class StepObservation:
    """Immutable-style snapshot returned by any EnvironmentAdapter.step()."""

    raw_frame: np.ndarray
    display_frame: np.ndarray
    native_reward: float
    shaped_reward: float
    health: float
    ammo: float
    ammo_max: float
    kills: int
    total_kills: int
    shots_fired: int
    shots_hit: int
    total_shots: int
    total_hits: int
    episode: int
    episode_steps: int
    episode_reward: float
    episode_finished: bool
    last_episode: dict[str, Any]
    enemy_overlay: dict[str, Any]
    action_name: str
    mode: str
    scenario_id: str


@dataclass
class ActionDecision:
    """Structured output from an RLAgent action selection."""

    action_idx: int
    action_name: str
    action_prob: float
    action_probs: list[float]
    value: float = 0.0
    log_prob: float = 0.0
    entropy: float = 0.0


class VisualPreprocessor(ABC):
    """Transforms raw RGB visual buffers into normalized RL observation tensors."""

    @property
    @abstractmethod
    def output_shape(self) -> tuple[int, ...]:
        """Expected observation tensor shape, e.g. (4, 84, 84)."""

    @abstractmethod
    def reset(self) -> None:
        """Clears any temporal frame buffer at episode boundaries."""

    @abstractmethod
    def process(self, rgb_frame: np.ndarray) -> np.ndarray:
        """Processes a raw RGB frame and returns the stacked observation tensor."""

    @abstractmethod
    def latest_frame(self) -> np.ndarray:
        """Returns the most recent stacked observation tensor."""

    @abstractmethod
    def compute_retina_64(self, rgb_frame: np.ndarray) -> np.ndarray:
        """Computes a 64x64 uint8 retinal matrix for the biological SNN."""


class RewardShaper(ABC):
    """Strategy interface for computing shaped RL rewards per scenario."""

    @abstractmethod
    def shape(
        self,
        *,
        action_name: str,
        native_reward: float,
        health_delta: float,
        ammo_before: float,
        ammo_delta: float,
        kills_added: int,
        prev_overlay: dict[str, Any],
        curr_overlay: dict[str, Any],
    ) -> float:
        """Computes a bounded shaped reward signal for the current transition."""


class EnvironmentAdapter(ABC):
    """Liskov-substitutable contract for ViZDoom and Synthetic environments."""

    @property
    @abstractmethod
    def scenario(self) -> ScenarioConfig:
        """Active scenario configuration."""

    @property
    @abstractmethod
    def action_labels(self) -> list[str]:
        """Ordered discrete action names."""

    @property
    @abstractmethod
    def mode(self) -> str:
        """Runtime mode: 'VIZDOOM_NATIVE' or 'SYNTHETIC_ARENA'."""

    @abstractmethod
    def reset(self) -> StepObservation:
        """Starts a new episode and returns the initial observation."""

    @abstractmethod
    def step(self, action_idx: int, action_name: str | None = None) -> StepObservation:
        """Executes one discrete action and returns the resulting observation."""

    @abstractmethod
    def set_tic_skip(self, tics: int) -> None:
        """Configures frame skip (simulation speed multiplier)."""

    @abstractmethod
    def set_skill(self, level: int) -> None:
        """Configures difficulty level (1..5)."""

    @abstractmethod
    def set_episode_timeout(self, tics: int) -> None:
        """Configures episode length limit in tics."""

    @abstractmethod
    def close(self) -> None:
        """Releases native game resources cleanly."""


class RLAgent(ABC):
    """Open/Closed contract for interchangeable RL algorithms (PPO, A2C, DQN)."""

    @property
    @abstractmethod
    def algorithm_name(self) -> str:
        """Human-readable algorithm name."""

    @abstractmethod
    def select_action(
        self,
        obs: np.ndarray,
        action_labels: list[str],
        greedy: bool | None = None,
    ) -> ActionDecision:
        """Selects an action given the processed visual buffer."""

    @abstractmethod
    def observe_transition(
        self,
        obs: np.ndarray,
        decision: ActionDecision,
        reward: float,
        done: bool,
    ) -> float | None:
        """Records transition and optionally performs an optimization step."""

    @abstractmethod
    def on_episode_end(self, summary: dict[str, Any]) -> float:
        """Finalizes episode metrics/learning and returns latest loss."""

    @abstractmethod
    def status(self) -> dict[str, Any]:
        """Returns serializable telemetry metrics for dashboards/APIs."""

    @abstractmethod
    def save(self, path: str | None = None, extra_stats: dict[str, Any] | None = None) -> None:
        """Persists agent weights and training state."""

    @abstractmethod
    def load(self, path: str | None = None) -> bool:
        """Restores agent weights and training state from disk."""

    @abstractmethod
    def reset(self) -> None:
        """Re-initializes model weights and training statistics."""


@runtime_checkable
class ConnectomeEngine(Protocol):
    """Protocol for the biophysical Drosophila SNN engine."""

    N: int
    num_synapses: int
    v_thresh: float
    dopamine_lr: float
    sensory_gain: float
    noise_std: float
    dopamine_level: float
    total_spikes_step: int
    last_latency_ms: float

    def step_biophysics(
        self, retina_matrix: np.ndarray, reward_signal: float = 0.0, dt: float = 1.0
    ) -> dict[str, float]: ...

    def update_biophysical_params(self, params: dict[str, Any]) -> None: ...

    def inject_dopamine_pulse(self, valence: float) -> None: ...

    def get_plasticity_state(self) -> dict[str, Any]: ...

    def load_plasticity_state(self, state: dict[str, Any] | None) -> None: ...

    def reset_plasticity_state(self) -> None: ...


@runtime_checkable
class Neuromodulator(Protocol):
    """Protocol for asynchronous System-2 neuromodulation (e.g., Gemma 3)."""

    async def modulate(
        self, telemetry_summary: dict[str, Any], current_params: dict[str, float]
    ) -> dict[str, Any]: ...
