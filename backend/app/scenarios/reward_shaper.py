"""Pluggable Reward Shaping strategies per scenario category (OCP + SRP).

Includes bio-inspired Saccadic Visual Search shaping:
- Rewards sustained unidirectional sweeping when no enemy is in the visual field.
- Penalizes left-right jittering in place, idling at empty walls, or firing at air.
- Grants a Target Discovery bonus when a sweep brings a monster into view.
- Penalizes losing sight of an unkilled monster (teaches braking & locking on).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..core.interfaces import RewardShaper


def _turn_sign(action_name: str) -> int:
    """Returns -1 for left turn, +1 for right turn, 0 otherwise."""
    if "TURN_LEFT" in action_name:
        return -1
    if "TURN_RIGHT" in action_name:
        return 1
    return 0


class SaccadicSearchMixin:
    """Tracks angular sweep continuity when searching for off-screen enemies."""

    def __init__(self) -> None:
        self._scan_dir: int = 0
        self._scan_streak: int = 0

    def reset_search_state(self) -> None:
        self._scan_dir = 0
        self._scan_streak = 0

    def _score_visual_search(
        self,
        *,
        action_name: str,
        kills_added: int,
        prev_overlay: dict[str, Any],
        curr_overlay: dict[str, Any],
    ) -> float:
        prev_seen = prev_overlay.get("present", 0.0) > 0.5
        curr_seen = curr_overlay.get("present", 0.0) > 0.5
        turn_dir = _turn_sign(action_name)
        is_attack = "ATTACK" in action_name

        # Case 1: Sweeping just brought an enemy into the visual field -> Discovery Bonus!
        if not prev_seen and curr_seen:
            self._scan_streak = 0
            return 0.15

        # Case 2: Had an enemy in sight, didn't kill it, and turned away losing sight -> Penalty!
        if prev_seen and not curr_seen and kills_added == 0:
            self._scan_dir = -int(np.sign(float(prev_overlay.get("offset", 0.0)) or 1.0))
            self._scan_streak = 0
            return -0.09

        # Case 3: No enemy visible anywhere -> encourage continuous unidirectional 360° scan
        if not curr_seen:
            if is_attack:
                self._scan_streak = 0
                return -0.04
            if turn_dir != 0:
                if self._scan_dir == 0 or turn_dir == self._scan_dir:
                    self._scan_dir = turn_dir
                    self._scan_streak = min(24, self._scan_streak + 1)
                    return 0.022 + 0.001 * min(10, self._scan_streak)
                # Reversed turn direction while nothing is visible (useless L-R jitter)
                self._scan_dir = turn_dir
                self._scan_streak = 1
                return -0.018
            if "FORWARD" in action_name:
                return 0.008
            # Standing IDLE staring at an empty wall
            self._scan_streak = 0
            return -0.012

        # Case 4: Enemy is currently visible -> reset scan streak so agent focuses on aiming
        self._scan_streak = 0
        return 0.0


class CombatRewardShaper(SaccadicSearchMixin, RewardShaper):
    """Shaping for 360/line defense scenarios (defend_the_center, defend_the_line)."""

    def __init__(self) -> None:
        super().__init__()

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
        hits_added: int = 0,
    ) -> float:
        reward = float(native_reward)
        if health_delta < 0:
            reward -= 0.25

        reward += self._score_visual_search(
            action_name=action_name,
            kills_added=kills_added,
            prev_overlay=prev_overlay,
            curr_overlay=curr_overlay,
        )

        prev_seen = prev_overlay.get("present", 0.0) > 0.5
        curr_seen = curr_overlay.get("present", 0.0) > 0.5
        if prev_seen and curr_seen:
            reward += 0.55 * (
                abs(float(prev_overlay.get("offset", 0.0)))
                - abs(float(curr_overlay.get("offset", 0.0)))
            )

        is_attack = "ATTACK" in action_name
        is_turn = "TURN" in action_name or "MOVE" in action_name
        if curr_seen:
            offset = float(curr_overlay.get("offset", 0.0))
            if abs(offset) > 0.12:
                if prev_seen:
                    if "LEFT" in action_name and offset < 0:
                        reward += 0.035
                    elif "RIGHT" in action_name and offset > 0:
                        reward += 0.035
                    elif is_turn:
                        reward -= 0.015
            else:
                if is_attack and ammo_before > 0:
                    reward += 0.12
                elif is_attack:
                    reward -= 0.03
                elif is_turn:
                    reward -= 0.008
                elif action_name == "IDLE":
                    reward -= 0.004

        if kills_added > 0 or (ammo_delta > 0 and prev_overlay.get("centered", 0.0) > 0.5):
            reward += 0.05
        return float(np.clip(reward, -2.0, 2.0))


class BasicRewardShaper(RewardShaper):
    """Normalized shaping for basic/rocket/predict_position scenarios."""

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
        hits_added: int = 0,
    ) -> float:
        scaled = float(native_reward) * 0.02
        if kills_added > 0 and native_reward < 2.0:
            scaled += 1.2 * kills_added
        elif hits_added > 0:
            scaled += 0.25 * hits_added
        if prev_overlay.get("present", 0.0) > 0.5 and curr_overlay.get("present", 0.0) > 0.5:
            scaled += 0.18 * (
                abs(float(prev_overlay.get("offset", 0.0)))
                - abs(float(curr_overlay.get("offset", 0.0)))
            )
        return float(np.clip(scaled, -2.5, 2.5))


class CorridorRewardShaper(SaccadicSearchMixin, RewardShaper):
    """Shaping for deadly_corridor.cfg (forward progress + active scanning + combat)."""

    def __init__(self) -> None:
        super().__init__()

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
        hits_added: int = 0,
    ) -> float:
        reward = float(native_reward) * 0.05
        reward += 0.5 * self._score_visual_search(
            action_name=action_name,
            kills_added=kills_added,
            prev_overlay=prev_overlay,
            curr_overlay=curr_overlay,
        )
        if health_delta < 0:
            reward += health_delta * 0.015
        if kills_added > 0:
            reward += 0.45 * kills_added
        elif hits_added > 0:
            reward += 0.15 * hits_added
        if "FORWARD" in action_name:
            reward += 0.012
        return float(np.clip(reward, -2.5, 2.5))


class AssaultRewardShaper(SaccadicSearchMixin, RewardShaper):
    """Dense combat + 360° search shaping for Deathmatch & Freedoom2 campaign maps."""

    def __init__(self) -> None:
        super().__init__()

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
        hits_added: int = 0,
    ) -> float:
        reward = float(native_reward) * 0.05
        reward += self._score_visual_search(
            action_name=action_name,
            kills_added=kills_added,
            prev_overlay=prev_overlay,
            curr_overlay=curr_overlay,
        )

        if kills_added > 0:
            reward += 1.0 * kills_added
        if hits_added > kills_added:
            reward += 0.30 * (hits_added - kills_added)

        if health_delta < 0:
            reward += max(-0.6, health_delta * 0.015)
        elif health_delta > 0:
            reward += min(0.4, health_delta * 0.02)

        prev_seen = prev_overlay.get("present", 0.0) > 0.5
        curr_seen = curr_overlay.get("present", 0.0) > 0.5
        if prev_seen and curr_seen:
            reward += 0.45 * (
                abs(float(prev_overlay.get("offset", 0.0)))
                - abs(float(curr_overlay.get("offset", 0.0)))
            )

        if curr_seen:
            offset = float(curr_overlay.get("offset", 0.0))
            if abs(offset) > 0.14:
                if "LEFT" in action_name and offset < 0:
                    reward += 0.03
                elif "RIGHT" in action_name and offset > 0:
                    reward += 0.03
            elif "ATTACK" in action_name and ammo_before > 0:
                reward += 0.14

        return float(np.clip(reward, -2.5, 2.5))


class DodgeRewardShaper(RewardShaper):
    """Evasion shaping for take_cover.cfg against fireball-throwing DoomImps."""

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
        hits_added: int = 0,
    ) -> float:
        reward = float(native_reward) * 0.05
        if health_delta < 0:
            reward += max(-1.2, health_delta * 0.025)
        if "MOVE" in action_name:
            reward += 0.02
        return float(np.clip(reward, -2.0, 2.0))


class NavigationRewardShaper(SaccadicSearchMixin, RewardShaper):
    """Shaping for health_gathering.cfg (active scanning for medkits + survival)."""

    def __init__(self) -> None:
        super().__init__()

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
        hits_added: int = 0,
    ) -> float:
        reward = float(native_reward) * 0.05
        reward += 0.6 * self._score_visual_search(
            action_name=action_name,
            kills_added=0,
            prev_overlay=prev_overlay,
            curr_overlay=curr_overlay,
        )
        if health_delta > 0:
            reward += min(1.0, health_delta * 0.04)
        elif health_delta < 0:
            reward += max(-0.5, health_delta * 0.01)
        if "FORWARD" in action_name and curr_overlay.get("present", 0.0) > 0.5:
            reward += 0.025
        return float(np.clip(reward, -2.0, 2.0))


REWARD_SHAPER_REGISTRY: dict[str, type[RewardShaper]] = {
    "combat": CombatRewardShaper,
    "basic": BasicRewardShaper,
    "corridor": CorridorRewardShaper,
    "assault": AssaultRewardShaper,
    "dodge": DodgeRewardShaper,
    "navigation": NavigationRewardShaper,
}


def register_reward_shaper(name: str, shaper_cls: type[RewardShaper]) -> None:
    """Allows registering custom reward shapers without editing core code (OCP)."""
    REWARD_SHAPER_REGISTRY[name] = shaper_cls


def create_reward_shaper(name: str) -> RewardShaper:
    cls = REWARD_SHAPER_REGISTRY.get(name, CombatRewardShaper)
    return cls()
