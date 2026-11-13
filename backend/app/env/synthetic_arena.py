"""Synthetic fallback arena implementing EnvironmentAdapter (LSP-compliant)."""

from __future__ import annotations

import math

import cv2
import numpy as np

from ..core.interfaces import EnvironmentAdapter, RewardShaper, ScenarioConfig, StepObservation
from .overlay import EnemyOverlayDetector


class SyntheticArenaAdapter(EnvironmentAdapter):
    """Deterministic headless Cyber-Arena fallback when ViZDoom is unavailable."""

    def __init__(
        self,
        scenario: ScenarioConfig,
        reward_shaper: RewardShaper,
        *,
        skill: int = 3,
        tic_skip: int = 2,
        render_overlay: bool = True,
        episode_timeout: int = 300,
        legacy_reset_step: bool = False,
    ):
        self._scenario = scenario
        self._reward_shaper = reward_shaper
        self._overlay = EnemyOverlayDetector()
        self.skill = int(np.clip(skill, 1, 5))
        self.tic_skip = max(1, int(tic_skip))
        self.render_overlay = bool(render_overlay)
        self.synthetic_episode_timeout = max(1, int(episode_timeout))
        self.legacy_reset_step = bool(legacy_reset_step)

        self.ammo_max = float(scenario.ammo_max)
        self.episode_count = 1
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.tick = 0
        self.target_angle = 0.0
        self.last_health = 100.0
        self.last_ammo = self.ammo_max
        self.shots_fired = 0
        self.shots_hit = 0
        self.total_shots = 0
        self.total_hits = 0
        self.kills = 0
        self.total_kills = 0
        self.target_state = self._overlay.empty()
        self.last_episode_summary = self._make_summary()
        self.last_frame = np.zeros((240, 320, 3), dtype=np.uint8)

    @property
    def scenario(self) -> ScenarioConfig:
        return self._scenario

    @property
    def action_labels(self) -> list[str]:
        return [a.name for a in self._scenario.actions]

    @property
    def mode(self) -> str:
        return "SYNTHETIC_ARENA"

    def set_tic_skip(self, tics: int) -> None:
        self.tic_skip = max(1, int(tics))

    def set_skill(self, level: int) -> None:
        self.skill = int(np.clip(level, 1, 5))

    def set_episode_timeout(self, tics: int) -> None:
        self.synthetic_episode_timeout = max(1, int(tics))

    def close(self) -> None:
        return None

    def _make_summary(self) -> dict:
        return {
            "episode": self.episode_count,
            "reward": round(self.episode_reward, 3),
            "kills": self.kills,
            "shots": self.shots_fired,
            "hits": self.shots_hit,
            "accuracy": round(self.shots_hit / max(1, self.shots_fired), 3),
            "steps": self.episode_steps,
            "scenario_id": self._scenario.id,
        }

    def _reset_counters(self) -> None:
        self.last_health = 100.0
        self.last_ammo = self.ammo_max
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.shots_fired = 0
        self.shots_hit = 0
        self.kills = 0
        self.target_angle = 0.0
        self.target_state = self._overlay.empty()

    def _episode_banner(self) -> np.ndarray:
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.putText(
            frame,
            f"EPISODE {self.episode_count}",
            (78, 108),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.85,
            (0, 255, 180),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            self._scenario.id.upper(),
            (70, 140),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (148, 163, 184),
            1,
            cv2.LINE_AA,
        )
        return frame

    def reset(self) -> StepObservation:
        if self.episode_steps > 0:
            self.last_episode_summary = self._make_summary()
        self._reset_counters()
        frame = self._render_frame("IDLE")[0]
        self.last_frame = frame.copy()
        self.target_state = self._overlay.detect(
            frame, None, is_combat=self._scenario.is_combat
        )
        display = (
            self._overlay.draw_overlay(frame.copy(), self.target_state, self._scenario.is_combat)
            if self.render_overlay
            else frame
        )
        return StepObservation(
            raw_frame=frame,
            display_frame=display,
            native_reward=0.0,
            shaped_reward=0.0,
            health=self.last_health,
            ammo=self.last_ammo,
            ammo_max=self.ammo_max,
            kills=self.kills,
            total_kills=self.total_kills,
            shots_fired=self.shots_fired,
            shots_hit=self.shots_hit,
            total_shots=self.total_shots,
            total_hits=self.total_hits,
            episode=self.episode_count,
            episode_steps=self.episode_steps,
            episode_reward=0.0,
            episode_finished=False,
            last_episode=self.last_episode_summary,
            enemy_overlay=dict(self.target_state),
            action_name="EPISODE_START",
            mode=self.mode,
            scenario_id=self._scenario.id,
        )

    def _render_frame(self, action_name: str) -> tuple[np.ndarray, float, int, int, float]:
        self.tick += 1
        if "LEFT" in action_name:
            self.target_angle += 0.12
        elif "RIGHT" in action_name:
            self.target_angle -= 0.12

        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        if self._scenario.is_combat:
            frame[:120, :] = (28, 18, 38)
            frame[120:, :] = (42, 38, 45)
        else:
            frame[:120, :] = (18, 28, 24)
            frame[120:, :] = (25, 58, 34)

        speed = 0.06 + 0.02 * self.skill
        self.target_angle += math.sin(self.tick * 0.05) * speed
        cx = int(160 + math.sin(self.target_angle) * 110)
        cy = 115
        radius = int(26 + 8 * math.cos(self.tick * 0.08) + (self.skill - 3) * 2)

        if self._scenario.is_combat:
            cv2.circle(frame, (cx, cy), radius, (235, 50, 40), -1)
            cv2.circle(frame, (cx - 8, cy - 6), 4, (255, 255, 100), -1)
            cv2.circle(frame, (cx + 8, cy - 6), 4, (255, 255, 100), -1)
        else:
            cv2.rectangle(frame, (cx - 18, cy - 14), (cx + 18, cy + 14), (40, 190, 220), -1)
            cv2.line(frame, (cx - 8, cy), (cx + 8, cy), (255, 255, 255), 3)
            cv2.line(frame, (cx, cy - 8), (cx, cy + 8), (255, 255, 255), 3)

        cv2.line(frame, (152, 120), (168, 120), (0, 255, 180), 1)
        cv2.line(frame, (160, 112), (160, 128), (0, 255, 180), 1)

        reward = 0.0
        shots = 0
        kills_added = 0
        health_delta = 0.0

        if self._scenario.is_combat:
            if "ATTACK" in action_name and self.last_ammo > 0:
                self.last_ammo = max(0.0, self.last_ammo - 1.0)
                self.shots_fired += 1
                self.total_shots += 1
                shots = 1
                cv2.circle(frame, (160, 195), 28, (255, 200, 60), -1)
                if abs(cx - 160) < 32:
                    reward = 1.0
                    kills_added = 1
                    self.kills += 1
                    self.total_kills += 1
                    self.shots_hit += 1
                    self.total_hits += 1
                    cv2.circle(frame, (cx, cy), radius + 6, (255, 255, 255), 3)
                else:
                    reward = -0.05
        else:
            health_delta = -0.4
            if "FORWARD" in action_name and abs(cx - 160) < 42:
                health_delta = 20.0
                reward = 1.0
            else:
                reward = 0.05
            self.last_health = float(np.clip(self.last_health + health_delta, 0.0, 100.0))

        return frame, reward, shots, kills_added, health_delta

    def step(self, action_idx: int, action_name: str | None = None) -> StepObservation:
        actions = self._scenario.actions
        idx = int(np.clip(action_idx, 0, len(actions) - 1))
        resolved_name = action_name or actions[idx].name

        if self.legacy_reset_step and self.episode_steps >= self.synthetic_episode_timeout:
            summary = self._make_summary()
            self.last_episode_summary = summary
            self.episode_count += 1
            self._reset_counters()
            banner = self._episode_banner()
            self.last_frame = banner.copy()
            return StepObservation(
                raw_frame=banner,
                display_frame=banner,
                native_reward=0.0,
                shaped_reward=0.0,
                health=self.last_health,
                ammo=self.last_ammo,
                ammo_max=self.ammo_max,
                kills=0,
                total_kills=self.total_kills,
                shots_fired=0,
                shots_hit=0,
                total_shots=self.total_shots,
                total_hits=self.total_hits,
                episode=self.episode_count,
                episode_steps=0,
                episode_reward=0.0,
                episode_finished=True,
                last_episode=summary,
                enemy_overlay=self._overlay.empty(),
                action_name="EPISODE_RESET",
                mode=self.mode,
                scenario_id=self._scenario.id,
            )

        prev_overlay = dict(self.target_state)
        ammo_before = self.last_ammo
        rgb_frame, native_reward, shots, kills_added, health_delta = self._render_frame(
            resolved_name
        )
        curr_overlay = self._overlay.detect(
            rgb_frame, None, is_combat=self._scenario.is_combat
        )
        self.target_state = curr_overlay
        ammo_delta = max(0.0, ammo_before - self.last_ammo)

        shaped = self._reward_shaper.shape(
            action_name=resolved_name,
            native_reward=native_reward,
            health_delta=health_delta,
            ammo_before=ammo_before,
            ammo_delta=ammo_delta,
            kills_added=kills_added,
            prev_overlay=prev_overlay,
            curr_overlay=curr_overlay,
        )
        self.episode_reward += shaped
        self.episode_steps += 1
        self.last_frame = rgb_frame.copy()

        display = (
            self._overlay.draw_overlay(rgb_frame.copy(), curr_overlay, self._scenario.is_combat)
            if self.render_overlay
            else rgb_frame
        )

        # Standard RL / PPO mode: emit terminal transition immediately on final step
        if not self.legacy_reset_step and (
            self.episode_steps >= self.synthetic_episode_timeout or self.last_health <= 0.0
        ):
            ep_kills = self.kills
            ep_shots = self.shots_fired
            ep_hits = self.shots_hit
            ep_steps = self.episode_steps
            ep_reward = round(float(self.episode_reward), 2)
            ep_num = self.episode_count
            summary = self._make_summary()
            self.last_episode_summary = summary
            self.episode_count += 1
            self._reset_counters()
            return StepObservation(
                raw_frame=rgb_frame,
                display_frame=display,
                native_reward=float(native_reward),
                shaped_reward=round(float(shaped), 4),
                health=round(float(self.last_health), 1),
                ammo=round(float(self.last_ammo), 1),
                ammo_max=self.ammo_max,
                kills=ep_kills,
                total_kills=self.total_kills,
                shots_fired=ep_shots,
                shots_hit=ep_hits,
                total_shots=self.total_shots,
                total_hits=self.total_hits,
                episode=ep_num,
                episode_steps=ep_steps,
                episode_reward=ep_reward,
                episode_finished=True,
                last_episode=summary,
                enemy_overlay=curr_overlay,
                action_name=resolved_name,
                mode=self.mode,
                scenario_id=self._scenario.id,
            )

        return StepObservation(
            raw_frame=rgb_frame,
            display_frame=display,
            native_reward=float(native_reward),
            shaped_reward=round(float(shaped), 4),
            health=round(float(self.last_health), 1),
            ammo=round(float(self.last_ammo), 1),
            ammo_max=self.ammo_max,
            kills=self.kills,
            total_kills=self.total_kills,
            shots_fired=self.shots_fired,
            shots_hit=self.shots_hit,
            total_shots=self.total_shots,
            total_hits=self.total_hits,
            episode=self.episode_count,
            episode_steps=self.episode_steps,
            episode_reward=round(float(self.episode_reward), 2),
            episode_finished=False,
            last_episode=self.last_episode_summary,
            enemy_overlay=curr_overlay,
            action_name=resolved_name,
            mode=self.mode,
            scenario_id=self._scenario.id,
        )
