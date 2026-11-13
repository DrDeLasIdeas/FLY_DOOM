"""Backward-compatible facade over ScenarioFactory, EnvironmentAdapter, and VisualBufferProcessor.

Preserves existing callers and tests (DoomFlyEnvironment) while delegating
environment execution, reward shaping, and visual buffering to SOLID modules.
"""

from __future__ import annotations

import base64

import cv2
import numpy as np

from .env.vizdoom_adapter import VIZDOOM_AVAILABLE
from .scenarios.factory import ScenarioFactory
from .vision.preprocessor import VisualBufferProcessor

ACTION_NAMES = [
    "TURN_LEFT (DNp20_L)",
    "TURN_RIGHT (DNp20_R)",
    "ATTACK (DNp09)",
    "IDLE",
]


class DoomFlyEnvironment:
    """Facade wrapping ScenarioFactory + VisualBufferProcessor for legacy callers."""

    def __init__(
        self,
        force_synthetic: bool = False,
        encode_frames: bool = True,
        render_overlay: bool = True,
        skill: int = 3,
        scenario_id: str = "defend_the_center",
    ):
        self.encode_frames = bool(encode_frames)
        self.render_overlay = bool(render_overlay)
        self._factory = ScenarioFactory()
        self._processor = VisualBufferProcessor()
        effective_synthetic = bool(force_synthetic or not VIZDOOM_AVAILABLE)
        self._adapter = self._factory.create(
            scenario_id=scenario_id,
            force_synthetic=effective_synthetic,
            skill=skill,
            render_overlay=self.render_overlay,
        )

    @property
    def use_synthetic(self) -> bool:
        return self._adapter.mode == "SYNTHETIC_ARENA"

    @property
    def ammo_max(self) -> float:
        return self._adapter.ammo_max

    @property
    def synthetic_episode_timeout(self) -> int:
        return getattr(self._adapter, "synthetic_episode_timeout", 300)

    @synthetic_episode_timeout.setter
    def synthetic_episode_timeout(self, value: int) -> None:
        if hasattr(self._adapter, "synthetic_episode_timeout"):
            self._adapter.synthetic_episode_timeout = max(1, int(value))

    @property
    def last_ammo(self) -> float:
        return self._adapter.last_ammo

    @last_ammo.setter
    def last_ammo(self, value: float) -> None:
        self._adapter.last_ammo = float(value)

    @property
    def shots_fired(self) -> int:
        return self._adapter.shots_fired

    @property
    def kills(self) -> int:
        return self._adapter.kills

    @property
    def total_kills(self) -> int:
        return self._adapter.total_kills

    @total_kills.setter
    def total_kills(self, value: int) -> None:
        self._adapter.total_kills = int(value)

    @property
    def total_shots(self) -> int:
        return self._adapter.total_shots

    @total_shots.setter
    def total_shots(self, value: int) -> None:
        self._adapter.total_shots = int(value)

    @property
    def total_hits(self) -> int:
        return self._adapter.total_hits

    @total_hits.setter
    def total_hits(self, value: int) -> None:
        self._adapter.total_hits = int(value)

    def set_tic_skip(self, tics: int) -> None:
        self._adapter.set_tic_skip(tics)

    def set_skill(self, level: int) -> None:
        self._adapter.set_skill(level)

    def set_episode_timeout(self, tics: int) -> None:
        self._adapter.set_episode_timeout(tics)

    def close(self) -> None:
        self._adapter.close()

    def enemy_state_snapshot(self) -> dict:
        if hasattr(self._adapter, "enemy_state"):
            return dict(self._adapter.enemy_state)
        if hasattr(self._adapter, "target_state"):
            return dict(self._adapter.target_state)
        return {"present": 0.0, "offset": 0.0, "size": 0.0, "centered": 0.0}

    def _make_summary(self) -> dict:
        return self._adapter._make_summary()

    def _reset_counters(self) -> None:
        self._adapter._reset_counters()

    @staticmethod
    def _decode_motor_command(dn_rates: dict) -> tuple[int, str]:
        turn_diff = dn_rates["dn_right"] - dn_rates["dn_left"]
        attack_drive = dn_rates["dn_attack"]
        if attack_drive > 0.085 and attack_drive >= abs(turn_diff):
            return 2, "ATTACK (DNp09)"
        if turn_diff > 0.006:
            return 1, "TURN_RIGHT (DNp20_R)"
        if turn_diff < -0.006:
            return 0, "TURN_LEFT (DNp20_L)"
        return (1 if turn_diff >= 0 else 0), "MICRO_SACCADE"

    def step(
        self,
        dn_rates: dict | None = None,
        action_idx: int | None = None,
        action_name: str | None = None,
    ) -> dict:
        if action_idx is None:
            if dn_rates is None:
                raise ValueError("Se requiere dn_rates o action_idx")
            action_idx, action_name = self._decode_motor_command(dn_rates)
        else:
            action_idx = int(np.clip(action_idx, 0, len(self._adapter.action_labels) - 1))
            action_name = action_name or ACTION_NAMES[min(action_idx, len(ACTION_NAMES) - 1)]

        obs = self._adapter.step(action_idx=action_idx, action_name=action_name)
        if obs.episode_finished:
            self._processor.reset()
        else:
            self._processor.process(obs.raw_frame)
        retina_64 = self._processor.compute_retina_64(obs.raw_frame)

        if self.encode_frames:
            bgr = cv2.cvtColor(obs.display_frame, cv2.COLOR_RGB2BGR)
            _, buffer = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            frame_b64 = base64.b64encode(buffer).decode("utf-8")

            _, ret_buf = cv2.imencode(".jpg", retina_64, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            retina_b64 = base64.b64encode(ret_buf).decode("utf-8")
        else:
            frame_b64 = ""
            retina_b64 = ""

        return {
            "retina_64": retina_64,
            "frame_b64": frame_b64,
            "retina_b64": retina_b64,
            "bio_reward": float(obs.native_reward),
            "shaped_reward": float(obs.shaped_reward),
            "action_name": obs.action_name,
            "health": obs.health,
            "ammo": obs.ammo,
            "ammo_max": obs.ammo_max,
            "kills": obs.kills,
            "total_kills": obs.total_kills,
            "shots_fired": obs.shots_fired,
            "shots_hit": obs.shots_hit,
            "total_shots": obs.total_shots,
            "total_hits": obs.total_hits,
            "accuracy": round(obs.shots_hit / max(1, obs.shots_fired), 3),
            "enemy": obs.enemy_overlay,
            "episode": obs.episode,
            "episode_reward": obs.episode_reward,
            "episode_finished": obs.episode_finished,
            "last_episode": obs.last_episode,
            "tic_skip": self._adapter.tic_skip,
            "mode": obs.mode,
        }
