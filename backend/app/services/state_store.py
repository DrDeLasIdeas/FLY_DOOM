"""SystemStateStore — SRP service handling atomic state persistence across SNN, RL & Env."""

from __future__ import annotations

import time
from typing import Any

import numpy as np


class SystemStateStore:
    """Synchronizes and persists RL checkpoints, SNN R-STDP plasticity, and combat totals."""

    def sync_env_totals_from_agent(self, env: Any, agent: Any) -> None:
        if hasattr(env, "total_kills"):
            env.total_kills = max(getattr(env, "total_kills", 0), agent.total_kills)
        if hasattr(env, "total_shots"):
            env.total_shots = max(getattr(env, "total_shots", 0), agent.total_shots)
        if hasattr(env, "total_hits"):
            env.total_hits = max(getattr(env, "total_hits", 0), agent.total_hits)

    def persist(
        self,
        *,
        agent: Any,
        snn_engine: Any,
        env: Any,
        stacked_obs: np.ndarray,
        system_running: bool,
        commit_partial: bool = False,
    ) -> dict[str, Any]:
        agent.snn_state = snn_engine.get_plasticity_state()
        live_kills = max(agent.total_kills, getattr(env, "total_kills", 0))
        live_shots = max(agent.total_shots, getattr(env, "total_shots", 0))
        live_hits = max(agent.total_hits, getattr(env, "total_hits", 0))

        if commit_partial and hasattr(agent, "buffer") and len(agent.buffer) >= 2:
            agent.update(stacked_obs, False)

        live_acc = live_hits / max(1, live_shots)
        agent.total_kills = live_kills
        agent.total_shots = live_shots
        agent.total_hits = live_hits
        agent.accuracy = live_acc
        agent.save(
            extra_stats={
                "total_kills": live_kills,
                "total_shots": live_shots,
                "total_hits": live_hits,
                "accuracy": live_acc,
                "best_kills": max(agent.best_kills, live_kills),
            }
        )
        saved_at = round(time.time(), 3)
        return {
            "system_running": system_running,
            "last_saved_at": saved_at,
            "scenario_id": env.scenario.id,
            "episodes": agent.episode,
            "total_kills": live_kills,
            "total_shots": live_shots,
            "total_hits": live_hits,
            "motor_gains": [
                round(float(g), 3)
                for g in snn_engine.motor_plastic_gain.detach().cpu().numpy()
            ],
        }
