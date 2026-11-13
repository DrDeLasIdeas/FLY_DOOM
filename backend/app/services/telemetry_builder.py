"""TelemetryPacketBuilder — SRP service for frame encoding, FPS tracking, and WS JSON assembly."""

from __future__ import annotations

import base64
import time
from collections import deque
from typing import Any

import cv2
import numpy as np

from ..config import settings
from ..core.interfaces import ActionDecision, StepObservation


class TelemetryPacketBuilder:
    """Encodes visual frames, tracks real-time FPS, and builds WebSocket telemetry packets."""

    def __init__(self, initial_fps: float = 30.0):
        self._frame_timestamps: deque[float] = deque(maxlen=30)
        self.actual_fps: float = float(initial_fps)

    @staticmethod
    def encode_jpeg_b64(image: np.ndarray, *, is_rgb: bool = True, quality: int = 80) -> str:
        arr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) if is_rgb else image
        ok, buffer = cv2.imencode(".jpg", arr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not ok:
            return ""
        return base64.b64encode(buffer).decode("utf-8")

    def tick_fps(self) -> float:
        now = time.perf_counter()
        self._frame_timestamps.append(now)
        if len(self._frame_timestamps) >= 2:
            span = self._frame_timestamps[-1] - self._frame_timestamps[0]
            if span > 1e-6:
                self.actual_fps = round((len(self._frame_timestamps) - 1) / span, 1)
        return self.actual_fps

    def build_live_packet(
        self,
        *,
        step_obs: StepObservation,
        decision: ActionDecision,
        retina_64: np.ndarray,
        visual_processor: Any,
        env: Any,
        agent: Any,
        snn_engine: Any,
        latest_rates: dict[str, float],
        latest_gemma_state: dict[str, Any],
        scenario_status: dict[str, Any],
        system_running: bool,
        target_fps: int,
        last_saved_at: float | None,
    ) -> dict[str, Any]:
        actual_fps = self.tick_fps()
        frame_b64 = self.encode_jpeg_b64(step_obs.display_frame, is_rgb=True, quality=80)
        retina_b64 = self.encode_jpeg_b64(retina_64, is_rgb=False, quality=85)
        visual_buffer_b64 = visual_processor.encode_stack_mosaic_b64(quality=80)

        live_acc = round(step_obs.total_hits / max(1, step_obs.total_shots), 3)
        attack_idx = next(
            (i for i, lbl in enumerate(env.action_labels) if "ATTACK" in lbl),
            None,
        )
        attack_power = (
            decision.action_probs[attack_idx]
            if attack_idx is not None and attack_idx < len(decision.action_probs)
            else 0.0
        )

        tic_skip = getattr(env, "tic_skip", 2)
        return {
            "timestamp": round(time.time(), 3),
            "system_running": system_running,
            "last_saved_at": last_saved_at,
            "actual_fps": actual_fps,
            "target_fps": target_fps,
            "tic_skip": tic_skip,
            "frame_b64": frame_b64,
            "retina_b64": retina_b64,
            "visual_buffer_b64": visual_buffer_b64,
            "visual_buffer_shape": list(visual_processor.output_shape),
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
            "scenario": scenario_status,
            "rates": latest_rates,
            "biophysics": {
                "v_thresh": round(snn_engine.v_thresh, 2),
                "dopamine_lr": round(snn_engine.dopamine_lr, 4),
                "sensory_gain": round(snn_engine.sensory_gain, 1),
                "noise_std": round(snn_engine.noise_std, 2),
                "dopamine_level": round(snn_engine.dopamine_level, 3),
                "total_spikes": snn_engine.total_spikes_step,
                "latency_ms": snn_engine.last_latency_ms,
                "motor_gains": [
                    round(float(g), 3)
                    for g in snn_engine.motor_plastic_gain.detach().cpu().numpy()
                ],
                "v_rest": snn_engine.v_rest,
                "v_reset": snn_engine.v_reset,
                "tau_m": snn_engine.tau_m,
                "tau_syn": snn_engine.tau_syn,
                "substeps": settings.substeps_per_frame,
                "num_synapses": snn_engine.num_synapses,
                "device": str(snn_engine.device),
            },
            "lif_trace": snn_engine.get_lif_trace(),
            "gemma": latest_gemma_state,
            "connectome": snn_engine.get_dynamic_activity(),
            "neurons_3d": snn_engine.get_sampled_3d_activity(360),
            "policy": {
                **agent.status(),
                "total_kills": step_obs.total_kills,
                "total_shots": step_obs.total_shots,
                "total_hits": step_obs.total_hits,
                "best_kills": max(agent.best_kills, step_obs.total_kills),
                "accuracy": live_acc,
                "action_idx": decision.action_idx,
                "action_name": step_obs.action_name,
                "action_prob": round(decision.action_prob, 4),
                "action_probs": [round(p, 4) for p in decision.action_probs],
                "attack_power": round(float(attack_power), 4),
                "system_running": system_running,
                "actual_fps": actual_fps,
                "target_fps": target_fps,
                "tic_skip": tic_skip,
                "last_saved_at": last_saved_at,
            },
        }

    def build_paused_packet(
        self,
        *,
        cached_packet: dict[str, Any] | None,
        env: Any,
        agent: Any,
        latest_gemma_state: dict[str, Any],
        scenario_status: dict[str, Any],
        target_fps: int,
        last_saved_at: float | None,
    ) -> dict[str, Any] | None:
        if cached_packet is None:
            return None
        live_kills = getattr(env, "total_kills", agent.total_kills)
        live_shots = getattr(env, "total_shots", agent.total_shots)
        live_hits = getattr(env, "total_hits", agent.total_hits)
        tic_skip = getattr(env, "tic_skip", 2)
        return {
            **cached_packet,
            "timestamp": round(time.time(), 3),
            "system_running": False,
            "actual_fps": 0.0,
            "target_fps": target_fps,
            "tic_skip": tic_skip,
            "last_saved_at": last_saved_at,
            "action_name": "SISTEMA DETENIDO (GUARDADO)",
            "total_kills": live_kills,
            "total_shots": live_shots,
            "total_hits": live_hits,
            "gemma": latest_gemma_state,
            "scenario": scenario_status,
            "policy": {
                **cached_packet.get("policy", {}),
                **agent.status(),
                "total_kills": live_kills,
                "total_shots": live_shots,
                "total_hits": live_hits,
                "best_kills": max(agent.best_kills, live_kills),
                "accuracy": round(live_hits / max(1, live_shots), 3),
                "action_name": "SISTEMA DETENIDO (GUARDADO)",
                "system_running": False,
                "actual_fps": 0.0,
                "target_fps": target_fps,
                "tic_skip": tic_skip,
                "last_saved_at": last_saved_at,
            },
        }
