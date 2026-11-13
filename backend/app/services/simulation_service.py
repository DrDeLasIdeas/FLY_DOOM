"""SimulationCoordinator — DIP orchestrator decoupling FastAPI from RL, SNN, ViZDoom & Gemma 3."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import numpy as np

from ..config import settings
from ..connectome_snn import DrosophilaConnectomeEngine
from ..core.interfaces import EnvironmentAdapter, Neuromodulator, StepObservation
from ..gemma_neuromodulator import GemmaNeuromodulatorAdapter
from ..rl import PPOAgent, PPOConfig
from ..scenarios import ScenarioFactory
from ..vision import VisualBufferConfig, VisualBufferProcessor
from .state_store import SystemStateStore
from .telemetry_builder import TelemetryPacketBuilder


class SimulationCoordinator:
    """Coordinates VisualBuffer, PPOAgent, Drosophila SNN, EnvironmentAdapter, and Neuromodulator."""

    def __init__(
        self,
        *,
        snn_engine: DrosophilaConnectomeEngine | None = None,
        scenario_factory: ScenarioFactory | None = None,
        visual_processor: VisualBufferProcessor | None = None,
        rl_agent: PPOAgent | None = None,
        neuromodulator: Neuromodulator | None = None,
        packet_builder: TelemetryPacketBuilder | None = None,
        state_store: SystemStateStore | None = None,
        initial_scenario: str | None = None,
        target_fps: int | None = None,
    ):
        self.snn_engine = snn_engine or DrosophilaConnectomeEngine()
        self.scenario_factory = scenario_factory or ScenarioFactory()
        self.visual_processor = visual_processor or VisualBufferProcessor(
            VisualBufferConfig(width=84, height=84, stack_size=4)
        )
        self.neuromodulator: Neuromodulator = neuromodulator or GemmaNeuromodulatorAdapter()
        self.state_store = state_store or SystemStateStore()

        scenario_id = initial_scenario or settings.default_scenario
        self.env: EnvironmentAdapter = self.scenario_factory.create(
            scenario_id=scenario_id,
            tic_skip=2,
            render_overlay=True,
        )

        self.agent = rl_agent or PPOAgent(
            scenario_id=scenario_id,
            action_labels=self.env.action_labels,
            config=PPOConfig(checkpoint_dir=settings.checkpoint_dir),
        )
        self.agent.load()
        self.snn_engine.load_plasticity_state(self.agent.snn_state)
        self.state_store.sync_env_totals_from_agent(self.env, self.agent)

        self.lock = asyncio.Lock()
        self.system_running: bool = True
        self.target_fps: int = int(np.clip(target_fps or settings.target_fps, 5, 60))
        self.packet_builder = packet_builder or TelemetryPacketBuilder(
            initial_fps=float(self.target_fps)
        )
        self.last_saved_at: float | None = round(time.time(), 3) if self.agent.loaded else None
        self.last_packet_cache: dict[str, Any] | None = None
        self._bg_ppo_task: asyncio.Task | None = None

        self.latest_rates: dict[str, float] = {
            "retina_r1_r8": 0.0,
            "optic_lobe_t4_t5": 0.0,
            "mushroom_body_kc": 0.0,
            "central_complex": 0.0,
            "mbon_valence": 0.0,
            "dan_dopamine": 0.0,
            "dn_left": 0.01,
            "dn_right": 0.01,
            "dn_move": 0.01,
            "dn_attack": 0.01,
        }
        self.latest_gemma_state: dict[str, Any] = {
            "status": "INITIALIZING",
            "model": settings.ollama_model,
            "v_thresh": self.snn_engine.v_thresh,
            "dopamine_lr": self.snn_engine.dopamine_lr,
            "sensory_gain": self.snn_engine.sensory_gain,
            "noise_std": self.snn_engine.noise_std,
            "neuro_hypothesis": "Iniciando bucle neuroquímico Sistema 2...",
        }

        self._last_obs: StepObservation = self.env.reset()
        self._stacked_obs: np.ndarray = self.visual_processor.process(self._last_obs.raw_frame)
        self._last_retina: np.ndarray = self.visual_processor.compute_retina_64(
            self._last_obs.raw_frame
        )
        self._last_reward: float = 0.0

    @property
    def actual_fps(self) -> float:
        return self.packet_builder.actual_fps

    def _sync_env_totals_from_agent(self) -> None:
        self.state_store.sync_env_totals_from_agent(self.env, self.agent)

    def persist_state(self, commit_partial: bool = False) -> dict[str, Any]:
        saved = self.state_store.persist(
            agent=self.agent,
            snn_engine=self.snn_engine,
            env=self.env,
            stacked_obs=self._stacked_obs,
            system_running=self.system_running,
            commit_partial=commit_partial,
        )
        self.last_saved_at = saved["last_saved_at"]
        return saved

    def switch_scenario(self, scenario_id: str, skill: int | None = None) -> dict[str, Any]:
        self.persist_state(commit_partial=True)
        tic_skip = getattr(self.env, "tic_skip", 2)
        self.env.close()

        self.env = self.scenario_factory.create(
            scenario_id=scenario_id,
            skill=skill,
            tic_skip=tic_skip,
            render_overlay=True,
        )
        self.visual_processor.reset()
        self.agent.switch_scenario(scenario_id, self.env.action_labels, load_if_exists=True)
        self._sync_env_totals_from_agent()

        self._last_obs = self.env.reset()
        self._stacked_obs = self.visual_processor.process(self._last_obs.raw_frame)
        self._last_retina = self.visual_processor.compute_retina_64(self._last_obs.raw_frame)
        self._last_reward = 0.0
        self.last_packet_cache = None
        self.latest_gemma_state["neuro_hypothesis"] = (
            f"Escenario cambiado en caliente a '{self.env.scenario.name}' "
            f"({len(self.env.action_labels)} acciones)."
        )
        return self.scenario_status()

    def reset_episode(self) -> dict[str, Any]:
        self.visual_processor.reset()
        self._last_obs = self.env.reset()
        self._stacked_obs = self.visual_processor.process(self._last_obs.raw_frame)
        self._last_retina = self.visual_processor.compute_retina_64(self._last_obs.raw_frame)
        self._last_reward = 0.0
        self.last_packet_cache = None
        return {
            "status": "episode_reset",
            "scenario_id": self.env.scenario.id,
            "episode": self._last_obs.episode,
        }

    def set_speed(
        self, *, target_fps: int | None = None, tic_skip: int | None = None
    ) -> dict[str, Any]:
        if target_fps is not None:
            self.target_fps = int(np.clip(target_fps, 5, 60))
        if tic_skip is not None:
            self.env.set_tic_skip(int(np.clip(tic_skip, 1, 8)))
        return {
            "status": "updated",
            "target_fps": self.target_fps,
            "tic_skip": getattr(self.env, "tic_skip", 2),
        }

    def scenario_status(self) -> dict[str, Any]:
        sc = self.env.scenario
        return {
            "id": sc.id,
            "name": sc.name,
            "description": sc.description,
            "cfg_file": sc.cfg_file,
            "is_combat": sc.is_combat,
            "actions": [{"name": a.name, "label": a.label} for a in sc.actions],
            "tic_skip": getattr(self.env, "tic_skip", 2),
            "target_fps": self.target_fps,
            "mode": self.env.mode,
            "available_scenarios": self.scenario_factory.list_scenarios(),
        }

    def health_status(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "device": str(self.snn_engine.device),
            "neurons": self.snn_engine.N,
            "synapses": self.snn_engine.num_synapses,
            "arena_mode": self.env.mode,
            "scenario_id": self.env.scenario.id,
            "algorithm": self.agent.algorithm_name,
            "policy_loaded": self.agent.loaded,
            "system_running": self.system_running,
            "total_kills": getattr(self.env, "total_kills", self.agent.total_kills),
            "episodes": self.agent.episode,
            "actual_fps": self.actual_fps,
            "target_fps": self.target_fps,
            "last_saved_at": self.last_saved_at,
        }

    def training_status(self) -> dict[str, Any]:
        status = self.agent.status()
        live_kills = max(status["total_kills"], getattr(self.env, "total_kills", 0))
        live_shots = max(status["total_shots"], getattr(self.env, "total_shots", 0))
        live_hits = max(status["total_hits"], getattr(self.env, "total_hits", 0))
        status.update(
            {
                "total_kills": live_kills,
                "total_shots": live_shots,
                "total_hits": live_hits,
                "best_kills": max(status["best_kills"], live_kills),
                "accuracy": round(live_hits / max(1, live_shots), 3),
                "system_running": self.system_running,
                "actual_fps": self.actual_fps,
                "target_fps": self.target_fps,
                "tic_skip": getattr(self.env, "tic_skip", 2),
                "last_saved_at": self.last_saved_at,
            }
        )
        return status

    async def _launch_async_ppo_update(self, job: dict[str, Any]) -> None:
        try:
            result = await asyncio.to_thread(self.agent.run_shadow_update, job)
            async with self.lock:
                self.agent.commit_shadow_update(result)
        except Exception as exc:
            print(f"[SimulationCoordinator] Error en actualización PPO asíncrona: {exc}")

    def _step_core(self, *, defer_ppo_update: bool = False) -> tuple[dict[str, Any], dict[str, Any] | None]:
        self.latest_rates = self.snn_engine.step_frame(
            self._last_retina,
            self._last_reward,
            substeps=settings.substeps_per_frame,
            dt=1.0,
        )
        self._last_reward = 0.0

        obs_tensor = self._stacked_obs
        decision = self.agent.select_action(obs_tensor, self.env.action_labels)
        prev_total_kills = getattr(self.env, "total_kills", 0)

        step_obs = self.env.step(decision.action_idx, decision.action_name)
        self._last_obs = step_obs
        self._last_retina = self.visual_processor.compute_retina_64(step_obs.raw_frame)
        self._last_reward = step_obs.native_reward

        pending_job: dict[str, Any] | None = None
        if step_obs.episode_finished:
            ready = self.agent.record_step(
                obs_tensor, decision, step_obs.shaped_reward, True
            )
            if ready:
                if defer_ppo_update:
                    pending_job = self.agent.prepare_async_update(obs_tensor, True)
                else:
                    self.agent.update(obs_tensor, True)
            self.agent.snn_state = self.snn_engine.get_plasticity_state()
            self.agent.on_episode_end(step_obs.last_episode)
            self.visual_processor.reset()
            self._stacked_obs = self.visual_processor.process(step_obs.raw_frame)
            self.last_saved_at = round(time.time(), 3)
        else:
            next_stack = self.visual_processor.process(step_obs.raw_frame)
            ready = self.agent.record_step(
                obs_tensor, decision, step_obs.shaped_reward, False
            )
            if ready:
                if defer_ppo_update:
                    pending_job = self.agent.prepare_async_update(next_stack, False)
                else:
                    self.agent.update(next_stack, False)
            self._stacked_obs = next_stack
            if step_obs.total_kills > prev_total_kills:
                self.persist_state(commit_partial=False)

        packet = self.packet_builder.build_live_packet(
            step_obs=step_obs,
            decision=decision,
            retina_64=self._last_retina,
            visual_processor=self.visual_processor,
            env=self.env,
            agent=self.agent,
            snn_engine=self.snn_engine,
            latest_rates=self.latest_rates,
            latest_gemma_state=self.latest_gemma_state,
            scenario_status=self.scenario_status(),
            system_running=self.system_running,
            target_fps=self.target_fps,
            last_saved_at=self.last_saved_at,
        )
        self.last_packet_cache = packet
        return packet, pending_job

    def step_simulation(self) -> dict[str, Any]:
        """Synchronous simulation step (for CLI / tests)."""
        packet, _ = self._step_core(defer_ppo_update=False)
        return packet

    async def step_simulation_async(self) -> dict[str, Any]:
        """Non-blocking simulation step for 30-60 Hz WebSocket streaming."""
        can_defer = self._bg_ppo_task is None or self._bg_ppo_task.done()
        async with self.lock:
            packet, job = self._step_core(defer_ppo_update=can_defer)
        if job is not None:
            self._bg_ppo_task = asyncio.create_task(self._launch_async_ppo_update(job))
        return packet

    def build_paused_packet(self) -> dict[str, Any] | None:
        return self.packet_builder.build_paused_packet(
            cached_packet=self.last_packet_cache,
            env=self.env,
            agent=self.agent,
            latest_gemma_state=self.latest_gemma_state,
            scenario_status=self.scenario_status(),
            target_fps=self.target_fps,
            last_saved_at=self.last_saved_at,
        )

    async def run_gemma_cycle(self) -> None:
        if not self.system_running:
            return
        current_params = {
            "v_thresh": self.snn_engine.v_thresh,
            "dopamine_lr": self.snn_engine.dopamine_lr,
            "sensory_gain": self.snn_engine.sensory_gain,
            "noise_std": self.snn_engine.noise_std,
        }
        result = await self.neuromodulator.modulate(self.latest_rates, current_params)
        self.snn_engine.update_biophysical_params(result)
        self.latest_gemma_state = result

    async def shutdown(self) -> None:
        if self._bg_ppo_task is not None and not self._bg_ppo_task.done():
            try:
                await self._bg_ppo_task
            except Exception:
                pass
        self.persist_state(commit_partial=True)
        self.env.close()
