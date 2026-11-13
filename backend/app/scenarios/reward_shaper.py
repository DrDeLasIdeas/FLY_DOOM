"""Pluggable Reward Shaping strategies per scenario category (OCP + SRP)."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..core.interfaces import RewardShaper


class CombatRewardShaper(RewardShaper):
    """Shaping for 360/line defense scenarios (defend_the_center, defend_the_line)."""

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
        reward = float(native_reward) + 0.001
        if health_delta < 0:
            reward -= 0.25
        if prev_overlay.get("present", 0.0) > 0.5 and curr_overlay.get("present", 0.0) > 0.5:
            reward += 0.5 * (
                abs(float(prev_overlay.get("offset", 0.0)))
                - abs(float(curr_overlay.get("offset", 0.0)))
            )

        is_attack = "ATTACK" in action_name
        is_turn = "TURN" in action_name or "MOVE" in action_name
        if curr_overlay.get("present", 0.0) > 0.5:
            offset = float(curr_overlay.get("offset", 0.0))
            if abs(offset) > 0.12:
                if "LEFT" in action_name and offset < 0:
                    reward += 0.03
                elif "RIGHT" in action_name and offset > 0:
                    reward += 0.03
                elif is_turn:
                    reward -= 0.01
            else:
                if is_attack and ammo_before > 0:
                    reward += 0.10
                elif is_attack:
                    reward -= 0.03
                elif is_turn:
                    reward -= 0.005
                elif action_name == "IDLE":
                    reward -= 0.002
        else:
            if is_attack:
                reward -= 0.03
            elif action_name == "IDLE":
                reward += 0.002
            elif is_turn:
                reward += 0.004

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


class CorridorRewardShaper(RewardShaper):
    """Shaping for deadly_corridor.cfg (forward progress + survival + combat)."""

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
            reward += health_delta * 0.015
        if kills_added > 0:
            reward += 0.45 * kills_added
        elif hits_added > 0:
            reward += 0.15 * hits_added
        if "FORWARD" in action_name:
            reward += 0.01
        return float(np.clip(reward, -2.5, 2.5))


class AssaultRewardShaper(RewardShaper):
    """Dense combat shaping for monster-filled arenas, Deathmatch & Freedoom2 maps."""

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
        reward = float(native_reward) * 0.05 + 0.002
        if kills_added > 0:
            reward += 1.0 * kills_added
        if hits_added > kills_added:
            reward += 0.30 * (hits_added - kills_added)

        if health_delta < 0:
            reward += max(-0.6, health_delta * 0.015)
        elif health_delta > 0:
            reward += min(0.4, health_delta * 0.02)

        if prev_overlay.get("present", 0.0) > 0.5 and curr_overlay.get("present", 0.0) > 0.5:
            reward += 0.35 * (
                abs(float(prev_overlay.get("offset", 0.0)))
                - abs(float(curr_overlay.get("offset", 0.0)))
            )

        is_attack = "ATTACK" in action_name
        if curr_overlay.get("present", 0.0) > 0.5:
            if curr_overlay.get("centered", 0.0) > 0.5 and is_attack and ammo_before > 0:
                reward += 0.12
        else:
            if is_attack:
                reward -= 0.03
            elif "FORWARD" in action_name or "TURN" in action_name:
                reward += 0.006

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


class NavigationRewardShaper(RewardShaper):
    """Shaping for health_gathering.cfg (survival + picking up medkits)."""

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
        if health_delta > 0:
            reward += min(1.0, health_delta * 0.04)
        elif health_delta < 0:
            reward += max(-0.5, health_delta * 0.01)
        if "FORWARD" in action_name:
            reward += 0.01
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
