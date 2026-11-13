"""ViZDoom native EnvironmentAdapter supporting multi-scenario .cfg/.wad."""

from __future__ import annotations

import os
import cv2
import numpy as np

from ..core.interfaces import EnvironmentAdapter, RewardShaper, ScenarioConfig, StepObservation
from .overlay import EnemyOverlayDetector
from .synthetic_arena import SyntheticArenaAdapter

try:
    import vizdoom as vzd

    VIZDOOM_AVAILABLE = True
except Exception:
    vzd = None
    VIZDOOM_AVAILABLE = False


class ViZDoomEnvironmentAdapter(EnvironmentAdapter):
    """Wraps vizdoom.DoomGame for any declarative ScenarioConfig with safe fallback."""

    def __init__(
        self,
        scenario: ScenarioConfig,
        reward_shaper: RewardShaper,
        *,
        skill: int = 3,
        tic_skip: int = 2,
        render_overlay: bool = True,
        legacy_reset_step: bool = False,
    ):
        if not VIZDOOM_AVAILABLE:
            raise RuntimeError("ViZDoom no está disponible en el entorno actual")

        self._scenario = scenario
        self._reward_shaper = reward_shaper
        self._overlay = EnemyOverlayDetector()
        self.skill = int(np.clip(skill, 1, 5))
        self.tic_skip = max(1, int(tic_skip))
        self.render_overlay = bool(render_overlay)
        self.legacy_reset_step = bool(legacy_reset_step)

        self.ammo_max = float(scenario.ammo_max)
        self.episode_count = 1
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.last_health = 100.0
        self.last_ammo = self.ammo_max
        self._last_killcount = 0
        self._last_hitcount = 0
        self.shots_fired = 0
        self.shots_hit = 0
        self.total_shots = 0
        self.total_hits = 0
        self.kills = 0
        self.total_kills = 0
        self.enemy_state = self._overlay.empty()
        self.last_episode_summary = self._make_summary()
        self.last_frame = np.zeros((240, 320, 3), dtype=np.uint8)
        self._fallback: SyntheticArenaAdapter | None = None

        self.game = vzd.DoomGame()
        if scenario.use_bundled_freedoom:
            fwad = os.path.join(os.path.dirname(vzd.__file__), "freedoom2.wad")
            self.game.set_doom_game_path(fwad)
            self.game.set_doom_scenario_path(fwad)
        else:
            if scenario.custom_cfg_path and os.path.exists(scenario.custom_cfg_path):
                cfg_path = scenario.custom_cfg_path
            elif os.path.isabs(scenario.cfg_file) and os.path.exists(scenario.cfg_file):
                cfg_path = scenario.cfg_file
            else:
                cfg_path = os.path.join(vzd.scenarios_path, scenario.cfg_file)
            self.game.load_config(cfg_path)
            if scenario.custom_wad_path and os.path.exists(scenario.custom_wad_path):
                self.game.set_doom_scenario_path(scenario.custom_wad_path)

        if scenario.doom_map:
            self.game.set_doom_map(scenario.doom_map)
        if scenario.episode_start_time is not None:
            self.game.set_episode_start_time(max(0, int(scenario.episode_start_time)))
        if scenario.living_reward is not None:
            self.game.set_living_reward(float(scenario.living_reward))
        if scenario.death_penalty is not None:
            self.game.set_death_penalty(float(scenario.death_penalty))

        # Enforce consistent RGB24 320x240 visual buffer across all scenarios
        self.game.set_screen_resolution(vzd.ScreenResolution.RES_320X240)
        self.game.set_screen_format(vzd.ScreenFormat.RGB24)
        self.game.set_window_visible(False)
        self.game.set_sound_enabled(False)
        self.game.set_render_hud(True)
        self.game.set_render_crosshair(scenario.is_combat)
        self.game.set_render_weapon(scenario.is_combat)
        self.game.set_labels_buffer_enabled(True)
        self.game.set_episode_timeout(max(100, int(scenario.episode_timeout)))
        self.game.set_doom_skill(self.skill)

        self.game.clear_available_buttons()
        for btn_name in scenario.buttons:
            self.game.add_available_button(getattr(vzd.Button, btn_name))

        self.game.clear_available_game_variables()
        for var_name in scenario.game_variables:
            if hasattr(vzd.GameVariable, var_name):
                self.game.add_available_game_variable(getattr(vzd.GameVariable, var_name))

        self.game.init()
        ammo, health, killcount, hitcount = self._query_engine_variables()
        if self._scenario.is_combat and ammo > self.ammo_max:
            self.ammo_max = ammo
        self.last_ammo = ammo
        self.last_health = health
        self._last_killcount = killcount
        self._last_hitcount = hitcount

    @property
    def scenario(self) -> ScenarioConfig:
        return self._scenario

    @property
    def action_labels(self) -> list[str]:
        return [a.name for a in self._scenario.actions]

    @property
    def mode(self) -> str:
        return "SYNTHETIC_ARENA" if self._fallback is not None else "VIZDOOM_NATIVE"

    def set_tic_skip(self, tics: int) -> None:
        self.tic_skip = max(1, int(tics))
        if self._fallback is not None:
            self._fallback.set_tic_skip(tics)

    def set_skill(self, level: int) -> None:
        self.skill = int(np.clip(level, 1, 5))
        if self._fallback is not None:
            self._fallback.set_skill(self.skill)
            return
        try:
            if not self.game.is_running():
                self.game.set_doom_skill(self.skill)
        except Exception:
            pass

    def set_episode_timeout(self, tics: int) -> None:
        if self._fallback is not None:
            self._fallback.set_episode_timeout(tics)
            return
        try:
            self.game.set_episode_timeout(max(50, int(tics)))
        except Exception:
            pass

    def close(self) -> None:
        if self._fallback is not None:
            self._fallback.close()
        if getattr(self, "game", None) is not None:
            try:
                self.game.close()
            except Exception:
                pass

    def _activate_fallback(self, reason: Exception | str) -> SyntheticArenaAdapter:
        if self._fallback is None:
            print(
                f"[ViZDoomAdapter] Conmutando '{self._scenario.id}' a Cyber-Arena Sintética ({reason})"
            )
            self._fallback = SyntheticArenaAdapter(
                scenario=self._scenario,
                reward_shaper=self._reward_shaper,
                skill=self.skill,
                tic_skip=self.tic_skip,
                render_overlay=self.render_overlay,
                legacy_reset_step=self.legacy_reset_step,
            )
            self._fallback.total_kills = self.total_kills
            self._fallback.total_shots = self.total_shots
            self._fallback.total_hits = self.total_hits
            self._fallback.episode_count = self.episode_count
        return self._fallback

    def _ensure_running(self) -> bool:
        if self._fallback is not None:
            return False
        try:
            if self.game.is_running():
                return True
        except Exception:
            pass
        try:
            self.game.close()
        except Exception:
            pass
        try:
            self.game.init()
            return True
        except Exception as exc:
            self._activate_fallback(exc)
            return False

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
        self._last_killcount = 0
        self._last_hitcount = 0
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.shots_fired = 0
        self.shots_hit = 0
        self.kills = 0
        self.enemy_state = self._overlay.empty()

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

    def _query_engine_variables(self) -> tuple[float, float, int, int]:
        """Queries weapon ammo, health, kills, and bullet/rocket hits directly from ViZDoom."""
        ammo = self.last_ammo
        health = self.last_health
        killcount = self._last_killcount
        hitcount = self._last_hitcount
        try:
            if self._scenario.is_combat:
                sel_ammo = float(self.game.get_game_variable(vzd.GameVariable.SELECTED_WEAPON_AMMO))
                ammo2 = float(self.game.get_game_variable(vzd.GameVariable.AMMO2))
                ammo = sel_ammo if sel_ammo >= 0.0 else max(0.0, ammo2)
            else:
                ammo = 0.0
            health = max(0.0, float(self.game.get_game_variable(vzd.GameVariable.HEALTH)))
            killcount = max(0, int(round(self.game.get_game_variable(vzd.GameVariable.KILLCOUNT))))
            hitcount = max(0, int(round(self.game.get_game_variable(vzd.GameVariable.HITCOUNT))))
        except Exception:
            pass
        return ammo, health, killcount, hitcount

    def _prime_new_episode(self) -> None:
        self._reset_counters()
        self.game.new_episode()
        ammo, health, killcount, hitcount = self._query_engine_variables()
        if self._scenario.is_combat and ammo > self.ammo_max:
            self.ammo_max = ammo
        self.last_ammo = ammo
        self.last_health = health
        self._last_killcount = killcount
        self._last_hitcount = hitcount
        state = self.game.get_state()
        if state is not None and state.screen_buffer is not None:
            self.last_frame = state.screen_buffer.copy()
            self.enemy_state = self._overlay.detect(
                state.screen_buffer, state.labels, is_combat=self._scenario.is_combat
            )

    def reset(self) -> StepObservation:
        if self._fallback is not None:
            return self._fallback.reset()
        if not self._ensure_running():
            return self._fallback.reset()  # type: ignore[union-attr]
        try:
            if self.episode_steps > 0:
                self.last_episode_summary = self._make_summary()
            self._prime_new_episode()
            rgb_frame = self.last_frame.copy()
            overlay = dict(self.enemy_state)
            display = (
                self._overlay.draw_overlay(rgb_frame.copy(), overlay, self._scenario.is_combat)
                if self.render_overlay
                else rgb_frame
            )
            return StepObservation(
                raw_frame=rgb_frame,
                display_frame=display,
                native_reward=0.0,
                shaped_reward=0.0,
                health=round(self.last_health, 1),
                ammo=round(self.last_ammo, 1),
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
                episode_finished=False,
                last_episode=self.last_episode_summary,
                enemy_overlay=overlay,
                action_name="EPISODE_START",
                mode=self.mode,
                scenario_id=self._scenario.id,
            )
        except Exception as exc:
            return self._activate_fallback(exc).reset()

    def step(self, action_idx: int, action_name: str | None = None) -> StepObservation:
        if self._fallback is not None:
            return self._fallback.step(action_idx, action_name)
        if not self._ensure_running():
            return self._fallback.step(action_idx, action_name)  # type: ignore[union-attr]

        actions = self._scenario.actions
        idx = int(np.clip(action_idx, 0, len(actions) - 1))
        spec = actions[idx]
        resolved_name = action_name or spec.name

        try:
            if self.game.is_episode_finished():
                if self.legacy_reset_step:
                    summary = self._make_summary()
                    self.last_episode_summary = summary
                    self.episode_count += 1
                    self._prime_new_episode()
                    banner = self._episode_banner()
                    return StepObservation(
                        raw_frame=banner,
                        display_frame=banner,
                        native_reward=0.0,
                        shaped_reward=0.0,
                        health=round(self.last_health, 1),
                        ammo=round(self.last_ammo, 1),
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
                self._prime_new_episode()

            prev_overlay = dict(self.enemy_state)
            ammo_before = self.last_ammo
            health_before = self.last_health
            killcount_before = self._last_killcount
            hitcount_before = self._last_hitcount

            native_reward = float(self.game.make_action(spec.buttons, self.tic_skip))
            finished_now = bool(self.game.is_episode_finished())
            ammo, health, killcount, hitcount = self._query_engine_variables()
            if self._scenario.is_combat and ammo > self.ammo_max:
                self.ammo_max = ammo

            state = None if finished_now else self.game.get_state()
            if state is not None and state.screen_buffer is not None:
                rgb_frame = state.screen_buffer
                labels = state.labels
            else:
                rgb_frame = self.last_frame.copy()
                labels = []

            health_delta = health - health_before
            ammo_delta = max(0.0, ammo_before - ammo)
            shots = int(round(ammo_delta)) if "ATTACK" in resolved_name else 0
            kills_added = max(0, killcount - killcount_before) if self._scenario.is_combat else 0
            raw_hits = max(0, hitcount - hitcount_before) if self._scenario.is_combat else 0
            hits_added = max(kills_added, raw_hits)

            if kills_added > 0:
                self.kills += kills_added
                self.total_kills += kills_added

            if hits_added > 0:
                shots = max(shots, hits_added)
                self.shots_hit += hits_added
                self.total_hits += hits_added

            if shots > 0:
                self.shots_fired += shots
                self.total_shots += shots

            self.last_health = health
            self.last_ammo = ammo
            self._last_killcount = killcount
            self._last_hitcount = hitcount
            curr_overlay = (
                self._overlay.detect(rgb_frame, labels, is_combat=self._scenario.is_combat)
                if not finished_now
                else prev_overlay
            )
            self.enemy_state = curr_overlay

            shaped = self._reward_shaper.shape(
                action_name=resolved_name,
                native_reward=native_reward,
                health_delta=health_delta,
                ammo_before=ammo_before,
                ammo_delta=ammo_delta,
                kills_added=kills_added,
                prev_overlay=prev_overlay,
                curr_overlay=curr_overlay,
                hits_added=hits_added,
            )
            self.episode_reward += shaped
            self.episode_steps += 1
            self.last_frame = rgb_frame.copy()

            display = (
                self._overlay.draw_overlay(rgb_frame.copy(), curr_overlay, self._scenario.is_combat)
                if self.render_overlay
                else rgb_frame
            )

            # Immediate terminal step handling for RL (preserves terminal reward in GAE)
            if finished_now and not self.legacy_reset_step:
                ep_kills = self.kills
                ep_shots = self.shots_fired
                ep_hits = self.shots_hit
                ep_steps = self.episode_steps
                ep_reward = round(float(self.episode_reward), 2)
                ep_num = self.episode_count
                summary = self._make_summary()
                self.last_episode_summary = summary
                self.episode_count += 1
                self._prime_new_episode()
                return StepObservation(
                    raw_frame=rgb_frame,
                    display_frame=display,
                    native_reward=float(native_reward),
                    shaped_reward=round(float(shaped), 4),
                    health=round(float(health), 1),
                    ammo=round(float(ammo), 1),
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
                health=round(float(health), 1),
                ammo=round(float(ammo), 1),
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
        except Exception as exc:
            return self._activate_fallback(exc).step(action_idx, action_name)
