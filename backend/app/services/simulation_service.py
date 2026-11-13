"""SimulationCoordinator — DIP-based orchestrator decoupling FastAPI from RL/SNN/ViZDoom."""

from __future__ import annotations

import asyncio
import base64
import time
from collections import deque
from typing import Any

import cv2
import numpy as np

from ..config import settings
from ..connectome_snn import DrosophilaConnectomeEngine
from ..core.interfaces import EnvironmentAdapter, StepObservation
from ..gemma_neuromodulator import query_local_gemma_neuromodulator
from ..rl import PPOAgent, PPOConfig
from ..scenarios import ScenarioFactory
from ..vision import VisualBufferConfig, VisualBufferProcessor


class SimulationCoordinator:
    """Coordinates VisualBuffer, PPOAgent, Drosophila SNN, ViZDoom, and Gemma 3."""

    def __init__(
        self,
        *,
        snn_engine: DrosophilaConnectomeEngine | None = None,
        scenario_factory: ScenarioFactory | None = None,
        visual_processor: VisualBufferProcessor | None = None,
        rl_agent: PPOAgent | None = None,
        initial_scenario: str | None = None,
        target_fps: int | None = None,
    ):
        self.snn_engine = snn_engine or DrosophilaConnectomeEngine()
        self.scenario_factory = scenario_factory or ScenarioFactory()
        self.visual_processor = visual_processor or VisualBufferProcessor(
            VisualBufferConfig(width=84, height=84, stack_size=4)
        )

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
        self._sync_env_totals_from_agent()

        self.lock = asyncio.Lock()
        self.system_running: bool = True
        self.target_fps: int = int(np.clip(target_fps or settings.target_fps, 5, 60))
        self.last_saved_at: float | None = round(time.time(), 3) if self.agent.loaded else None
        self.last_packet_cache: dict[str, Any] | None = None
        self._frame_timestamps: deque[float] = deque(maxlen=30)
        self.actual_fps: float = float(self.target_fps)

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

    def _sync_env_totals_from_agent(self) -> None:
        if hasattr(self.env, "total_kills"):
            self.env.total_kills = max(getattr(self.env, "total_kills", 0), self.agent.total_kills)
        if hasattr(self.env, "total_shots"):
            self.env.total_shots = max(getattr(self.env, "total_shots", 0), self.agent.total_shots)
        if hasattr(self.env, "total_hits"):
            self.env.total_hits = max(getattr(self.env, "total_hits", 0), self.agent.total_hits)

    @staticmethod
    def _encode_jpeg_b64(image: np.ndarray, *, is_rgb: bool = True, quality: int = 80) -> str:
        arr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) if is_rgb else image
        ok, buffer = cv2.imencode(".jpg", arr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not ok:
            return ""
        return base64.b64encode(buffer).decode("utf-8")

    def _update_fps(self) -> float:
        now = time.perf_counter()
        self._frame_timestamps.append(now)
        if len(self._frame_timestamps) >= 2:
            span = self._frame_timestamps[-1] - self._frame_timestamps[0]
            if span > 1e-6:
                self.actual_fps = round((len(self._frame_timestamps) - 1) / span, 1)
        return self.actual_fps

    def persist_state(self, commit_partial: bool = False) -> dict[str, Any]:
        self.agent.snn_state = self.snn_engine.get_plasticity_state()
        live_kills = max(self.agent.total_kills, getattr(self.env, "total_kills", 0))
        live_shots = max(self.agent.total_shots, getattr(self.env, "total_shots", 0))
        live_hits = max(self.agent.total_hits, getattr(self.env, "total_hits", 0))

        if commit_partial and len(self.agent.buffer) >= 2:
            self.agent.update(self._stacked_obs, False)

        live_acc = live_hits / max(1, live_shots)
        self.agent.total_kills = live_kills
        self.agent.total_shots = live_shots
        self.agent.total_hits = live_hits
        self.agent.accuracy = live_acc
        self.agent.save(
            extra_stats={
                "total_kills": live_kills,
                "total_shots": live_shots,
                "total_hits": live_hits,
                "accuracy": live_acc,
                "best_kills": max(self.agent.best_kills, live_kills),
            }
        )
        self.last_saved_at = round(time.time(), 3)
        return {
            "system_running": self.system_running,
            "last_saved_at": self.last_saved_at,
            "scenario_id": self.env.scenario.id,
            "episodes": self.agent.episode,
            "total_kills": live_kills,
            "total_shots": live_shots,
            "total_hits": live_hits,
            "motor_gains": [
                round(float(g), 3)
                for g in self.snn_engine.motor_plastic_gain.detach().cpu().numpy()
            ],
        }

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

    def set_speed(self, *, target_fps: int | None = None, tic_skip: int | None = None) -> dict[str, Any]:
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

    def step_simulation(self) -> dict[str, Any]:
        """Executes one complete biophysical + visual RL + environment telemetry cycle."""
        for _ in range(settings.substeps_per_frame):
            self.latest_rates = self.snn_engine.step_biophysics(
                self._last_retina, self._last_reward, dt=1.0
            )
            self._last_reward = 0.0

        obs_tensor = self._stacked_obs
        decision = self.agent.select_action(obs_tensor, self.env.action_labels)
        prev_total_kills = getattr(self.env, "total_kills", 0)

        step_obs = self.env.step(decision.action_idx, decision.action_name)
        self._last_obs = step_obs
        self._last_retina = self.visual_processor.compute_retina_64(step_obs.raw_frame)
        self._last_reward = step_obs.native_reward

        if step_obs.episode_finished:
            self.agent.observe_transition(
                obs_tensor,
                decision,
                step_obs.shaped_reward,
                True,
                next_obs=obs_tensor,
            )
            self.agent.snn_state = self.snn_engine.get_plasticity_state()
            self.agent.on_episode_end(step_obs.last_episode)
            self.visual_processor.reset()
            self._stacked_obs = self.visual_processor.process(step_obs.raw_frame)
            self.last_saved_at = round(time.time(), 3)
        else:
            next_stack = self.visual_processor.process(step_obs.raw_frame)
            self.agent.observe_transition(
                obs_tensor,
                decision,
                step_obs.shaped_reward,
                False,
                next_obs=next_stack,
            )
            self._stacked_obs = next_stack
            if step_obs.total_kills > prev_total_kills:
                self.persist_state(commit_partial=False)

        actual_fps = self._update_fps()
        frame_b64 = self._encode_jpeg_b64(step_obs.display_frame, is_rgb=True, quality=80)
        retina_b64 = self._encode_jpeg_b64(self._last_retina, is_rgb=False, quality=85)
        visual_buffer_b64 = self.visual_processor.encode_stack_mosaic_b64(quality=80)

        live_acc = round(step_obs.total_hits / max(1, step_obs.total_shots), 3)
        attack_idx = next(
            (i for i, lbl in enumerate(self.env.action_labels) if "ATTACK" in lbl),
            None,
        )
        attack_power = (
            decision.action_probs[attack_idx]
            if attack_idx is not None and attack_idx < len(decision.action_probs)
            else 0.0
        )

        packet = {
            "timestamp": round(time.time(), 3),
            "system_running": self.system_running,
            "last_saved_at": self.last_saved_at,
            "actual_fps": actual_fps,
            "target_fps": self.target_fps,
            "tic_skip": getattr(self.env, "tic_skip", 2),
            "frame_b64": frame_b64,
            "retina_b64": retina_b64,
            "visual_buffer_b64": visual_buffer_b64,
            "visual_buffer_shape": list(self.visual_processor.output_shape),
            "action_name": step_obs.action_name,
            "health": step_obs.health,
            "ammo": step_obs.ammo,
            "ammo_max": step_obs.ammo_max,
            "kills": step_obs.kills,
            "total_kills": step_obs.total_kills,
            "shots_fired": step_obs.shots_fired,
            "shots_hit": step_obs.shots_hit,
            "total_shots": step_obs.total_shots,
            "total_hits": step_obs.total_hits,
            "accuracy": round(step_obs.shots_hit / max(1, step_obs.shots_fired), 3),
            "enemy": step_obs.enemy_overlay,
            "shaped_reward": step_obs.shaped_reward,
            "episode": step_obs.episode,
            "episode_reward": step_obs.episode_reward,
            "episode_finished": step_obs.episode_finished,
            "last_episode": step_obs.last_episode,
            "arena_mode": step_obs.mode,
            "scenario": self.scenario_status(),
            "rates": self.latest_rates,
            "biophysics": {
                "v_thresh": round(self.snn_engine.v_thresh, 2),
                "dopamine_lr": round(self.snn_engine.dopamine_lr, 4),
                "sensory_gain": round(self.snn_engine.sensory_gain, 1),
                "noise_std": round(self.snn_engine.noise_std, 2),
                "dopamine_level": round(self.snn_engine.dopamine_level, 3),
                "total_spikes": self.snn_engine.total_spikes_step,
                "latency_ms": self.snn_engine.last_latency_ms,
                "motor_gains": [
                    round(float(g), 3)
                    for g in self.snn_engine.motor_plastic_gain.detach().cpu().numpy()
                ],
                "v_rest": self.snn_engine.v_rest,
                "v_reset": self.snn_engine.v_reset,
                "tau_m": self.snn_engine.tau_m,
                "tau_syn": self.snn_engine.tau_syn,
                "substeps": settings.substeps_per_frame,
                "num_synapses": self.snn_engine.num_synapses,
                "device": str(self.snn_engine.device),
            },
            "lif_trace": self.snn_engine.get_lif_trace(),
            "gemma": self.latest_gemma_state,
            "connectome": self.snn_engine.get_dynamic_activity(),
            "neurons_3d": self.snn_engine.get_sampled_3d_activity(360),
            "policy": {
                **self.agent.status(),
                "total_kills": step_obs.total_kills,
                "total_shots": step_obs.total_shots,
                "total_hits": step_obs.total_hits,
                "best_kills": max(self.agent.best_kills, step_obs.total_kills),
                "accuracy": live_acc,
                "action_idx": decision.action_idx,
                "action_name": step_obs.action_name,
                "action_prob": round(decision.action_prob, 4),
                "action_probs": [round(p, 4) for p in decision.action_probs],
                "attack_power": round(float(attack_power), 4),
                "system_running": self.system_running,
                "actual_fps": actual_fps,
                "target_fps": self.target_fps,
                "tic_skip": getattr(self.env, "tic_skip", 2),
                "last_saved_at": self.last_saved_at,
            },
        }
        self.last_packet_cache = packet
        return packet

    def build_paused_packet(self) -> dict[str, Any] | None:
        if self.last_packet_cache is None:
            return None
        live_kills = getattr(self.env, "total_kills", self.agent.total_kills)
        live_shots = getattr(self.env, "total_shots", self.agent.total_shots)
        live_hits = getattr(self.env, "total_hits", self.agent.total_hits)
        return {
            **self.last_packet_cache,
            "timestamp": round(time.time(), 3),
            "system_running": False,
            "actual_fps": 0.0,
            "target_fps": self.target_fps,
            "tic_skip": getattr(self.env, "tic_skip", 2),
            "last_saved_at": self.last_saved_at,
            "action_name": "SISTEMA DETENIDO (GUARDADO)",
            "total_kills": live_kills,
            "total_shots": live_shots,
            "total_hits": live_hits,
            "gemma": self.latest_gemma_state,
            "scenario": self.scenario_status(),
            "policy": {
                **self.last_packet_cache.get("policy", {}),
                **self.agent.status(),
                "total_kills": live_kills,
                "total_shots": live_shots,
                "total_hits": live_hits,
                "best_kills": max(self.agent.best_kills, live_kills),
                "accuracy": round(live_hits / max(1, live_shots), 3),
                "action_name": "SISTEMA DETENIDO (GUARDADO)",
                "system_running": False,
                "actual_fps": 0.0,
                "target_fps": self.target_fps,
                "tic_skip": getattr(self.env, "tic_skip", 2),
                "last_saved_at": self.last_saved_at,
            },
        }

    async def run_gemma_cycle(self) -> None:
        if not self.system_running:
            return
        current_params = {
            "v_thresh": self.snn_engine.v_thresh,
            "dopamine_lr": self.snn_engine.dopamine_lr,
            "sensory_gain": self.snn_engine.sensory_gain,
            "noise_std": self.snn_engine.noise_std,
        }
        result = await query_local_gemma_neuromodulator(self.latest_rates, current_params)
        self.snn_engine.update_biophysical_params(result)
        self.latest_gemma_state = result
