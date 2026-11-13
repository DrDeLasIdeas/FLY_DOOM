"""ScenarioFactory — instantiates ViZDoom or Synthetic adapters from ScenarioConfig."""

from __future__ import annotations

from ..core.interfaces import EnvironmentAdapter, ScenarioConfig
from ..env.synthetic_arena import SyntheticArenaAdapter
from ..env.vizdoom_adapter import VIZDOOM_AVAILABLE, ViZDoomEnvironmentAdapter
from .registry import ScenarioRegistry
from .reward_shaper import create_reward_shaper


class ScenarioFactory:
    """Factory that constructs EnvironmentAdapter instances for any registered scenario."""

    def __init__(self, registry: ScenarioRegistry | None = None):
        self.registry = registry or ScenarioRegistry()

    def list_scenarios(self) -> list[dict]:
        return self.registry.list_metadata()

    def get_config(self, scenario_id: str) -> ScenarioConfig:
        return self.registry.get(scenario_id)

    def create(
        self,
        scenario_id: str = "defend_the_center",
        *,
        force_synthetic: bool = False,
        skill: int | None = None,
        tic_skip: int = 2,
        render_overlay: bool = True,
        legacy_reset_step: bool = False,
    ) -> EnvironmentAdapter:
        config = self.registry.get(scenario_id)
        shaper = create_reward_shaper(config.reward_shaper)
        effective_skill = config.default_skill if skill is None else skill

        if force_synthetic or not VIZDOOM_AVAILABLE:
            return SyntheticArenaAdapter(
                scenario=config,
                reward_shaper=shaper,
                skill=effective_skill,
                tic_skip=tic_skip,
                render_overlay=render_overlay,
                legacy_reset_step=legacy_reset_step,
            )

        try:
            return ViZDoomEnvironmentAdapter(
                scenario=config,
                reward_shaper=shaper,
                skill=effective_skill,
                tic_skip=tic_skip,
                render_overlay=render_overlay,
                legacy_reset_step=legacy_reset_step,
            )
        except Exception as exc:
            print(
                f"[ScenarioFactory] Fallback a Cyber-Arena Sintética para '{scenario_id}' ({exc})"
            )
            return SyntheticArenaAdapter(
                scenario=config,
                reward_shaper=shaper,
                skill=effective_skill,
                tic_skip=tic_skip,
                render_overlay=render_overlay,
                legacy_reset_step=legacy_reset_step,
            )
