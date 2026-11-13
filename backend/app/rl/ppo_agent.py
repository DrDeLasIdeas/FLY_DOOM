"""Modular Proximal Policy Optimization (PPO) agent in pure PyTorch."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from ..core.interfaces import ActionDecision, RLAgent
from .networks import ActorCriticCNN
from .rollout_buffer import RolloutBuffer


@dataclass
class PPOConfig:
    """Hyperparameters for PPO over stacked visual frames."""

    in_channels: int = 4
    obs_height: int = 84
    obs_width: int = 84
    hidden_dim: int = 256
    lr: float = 2.5e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_coef: float = 0.2
    ent_coef: float = 0.015
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5
    rollout_steps: int = 128
    update_epochs: int = 4
    minibatch_size: int = 32
    temperature: float = 1.0
    checkpoint_dir: str = "checkpoints"


class PPOAgent(RLAgent):
    """Clipped PPO agent operating directly on processed visual FrameStack tensors."""

    def __init__(
        self,
        scenario_id: str = "defend_the_center",
        action_labels: list[str] | None = None,
        config: PPOConfig | None = None,
        save_path: str | None = None,
        device: str = "cpu",
    ):
        self.config = config or PPOConfig()
        self.device = torch.device(device)
        self.scenario_id = scenario_id
        self.action_labels = list(action_labels or ["TURN_LEFT", "TURN_RIGHT", "ATTACK", "IDLE"])
        self.n_actions = len(self.action_labels)
        self.save_path = save_path or os.path.join(
            self.config.checkpoint_dir, f"ppo_{self.scenario_id}.pt"
        )

        self.network = self._build_network(self.n_actions)
        self.optimizer = torch.optim.Adam(self.network.parameters(), lr=self.config.lr, eps=1e-5)
        self.buffer = RolloutBuffer()

        self.training_enabled: bool = True
        self.greedy: bool = False
        self.temperature: float = self.config.temperature
        self.loaded: bool = False

        # Episode & lifetime telemetry
        self.episode: int = 0
        self.total_steps: int = 0
        self.updates: int = 0
        self.best_reward: float = -1e9
        self.best_kills: int = 0
        self.avg_reward: float = 0.0
        self.total_kills: int = 0
        self.total_shots: int = 0
        self.total_hits: int = 0
        self.accuracy: float = 0.0
        self.last_loss: float = 0.0
        self.policy_loss: float = 0.0
        self.value_loss: float = 0.0
        self.entropy: float = math.log(max(2, self.n_actions))
        self.exploration_rate: float = 1.0
        self.approx_kl: float = 0.0
        self.clip_fraction: float = 0.0
        self.history: list[dict[str, Any]] = []
        self.snn_state: dict[str, Any] = {}

    @property
    def algorithm_name(self) -> str:
        return "PPO-CNN"

    def _build_network(self, n_actions: int) -> ActorCriticCNN:
        return ActorCriticCNN(
            in_channels=self.config.in_channels,
            n_actions=n_actions,
            obs_height=self.config.obs_height,
            obs_width=self.config.obs_width,
            hidden_dim=self.config.hidden_dim,
        ).to(self.device)

    def switch_scenario(
        self,
        scenario_id: str,
        action_labels: list[str],
        *,
        load_if_exists: bool = True,
    ) -> None:
        """Hot-swaps policy head & checkpoint path for a different ViZDoom scenario."""
        self.scenario_id = scenario_id
        self.action_labels = list(action_labels)
        new_n = len(self.action_labels)
        self.save_path = os.path.join(self.config.checkpoint_dir, f"ppo_{scenario_id}.pt")
        self.buffer.clear()

        if new_n != self.n_actions:
            self.n_actions = new_n
            self.network = self._build_network(new_n)
            self.optimizer = torch.optim.Adam(
                self.network.parameters(), lr=self.config.lr, eps=1e-5
            )
        else:
            self.n_actions = new_n

        self.episode = 0
        self.total_steps = 0
        self.updates = 0
        self.best_reward = -1e9
        self.best_kills = 0
        self.avg_reward = 0.0
        self.total_kills = 0
        self.total_shots = 0
        self.total_hits = 0
        self.accuracy = 0.0
        self.last_loss = 0.0
        self.policy_loss = 0.0
        self.value_loss = 0.0
        self.entropy = math.log(max(2, self.n_actions))
        self.exploration_rate = 1.0
        self.history.clear()
        self.loaded = False

        if load_if_exists and os.path.exists(self.save_path):
            self.load(self.save_path)

    def select_action(
        self,
        obs: np.ndarray,
        action_labels: list[str] | None = None,
        greedy: bool | None = None,
    ) -> ActionDecision:
        labels = action_labels or self.action_labels
        use_greedy = self.greedy if greedy is None else greedy
        idx, prob, probs, value, log_prob, entropy = self.network.act(
            obs,
            temperature=self.temperature,
            greedy=use_greedy,
            device=self.device,
        )
        max_ent = math.log(max(2, len(labels)))
        self.entropy = entropy
        self.exploration_rate = float(np.clip(entropy / max_ent, 0.0, 1.0))
        self.total_steps += 1
        return ActionDecision(
            action_idx=idx,
            action_name=labels[idx] if idx < len(labels) else f"ACTION_{idx}",
            action_prob=prob,
            action_probs=probs,
            value=value,
            log_prob=log_prob,
            entropy=entropy,
        )

    def observe_transition(
        self,
        obs: np.ndarray,
        decision: ActionDecision,
        reward: float,
        done: bool,
        *,
        next_obs: np.ndarray | None = None,
    ) -> float | None:
        if not self.training_enabled:
            return None
        self.buffer.add(
            obs=obs,
            action=decision.action_idx,
            log_prob=decision.log_prob,
            reward=reward,
            done=done,
            value=decision.value,
        )
        if len(self.buffer) >= self.config.rollout_steps:
            bootstrap_obs = next_obs if next_obs is not None else obs
            return self.update(bootstrap_obs, done)
        return None

    def update(self, last_obs: np.ndarray, last_done: bool) -> float:
        if len(self.buffer) < 2:
            self.buffer.clear()
            return 0.0

        with torch.no_grad():
            x = torch.as_tensor(last_obs, dtype=torch.float32, device=self.device).unsqueeze(0)
            _, next_val = self.network(x)
            last_value = float(next_val.item())

        advantages, returns = self.buffer.compute_gae(
            last_value=last_value,
            last_done=last_done,
            gamma=self.config.gamma,
            gae_lambda=self.config.gae_lambda,
        )

        total_losses: list[float] = []
        pg_losses: list[float] = []
        v_losses: list[float] = []
        entropies: list[float] = []
        kls: list[float] = []
        clips: list[float] = []

        for _ in range(max(1, self.config.update_epochs)):
            for batch in self.buffer.iter_minibatches(
                advantages,
                returns,
                minibatch_size=self.config.minibatch_size,
                device=self.device,
            ):
                new_logp, entropy, new_values = self.network.evaluate_actions(
                    batch.obs, batch.actions, temperature=self.temperature
                )
                log_ratio = new_logp - batch.old_log_probs
                ratio = torch.exp(log_ratio)

                with torch.no_grad():
                    approx_kl = ((ratio - 1.0) - log_ratio).mean().item()
                    clip_frac = (
                        ((ratio - 1.0).abs() > self.config.clip_coef).float().mean().item()
                    )
                    kls.append(float(approx_kl))
                    clips.append(float(clip_frac))

                pg_loss1 = -batch.advantages * ratio
                pg_loss2 = -batch.advantages * torch.clamp(
                    ratio, 1.0 - self.config.clip_coef, 1.0 + self.config.clip_coef
                )
                pg_loss = torch.max(pg_loss1, pg_loss2).mean()
                v_loss = 0.5 * F.mse_loss(new_values, batch.returns)
                ent_loss = entropy.mean()
                loss = pg_loss - self.config.ent_coef * ent_loss + self.config.vf_coef * v_loss

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.network.parameters(), self.config.max_grad_norm)
                self.optimizer.step()

                total_losses.append(float(loss.item()))
                pg_losses.append(float(pg_loss.item()))
                v_losses.append(float(v_loss.item()))
                entropies.append(float(ent_loss.item()))

        self.buffer.clear()
        self.updates += 1

        if total_losses:
            self.last_loss = float(np.mean(total_losses))
            self.policy_loss = float(np.mean(pg_losses))
            self.value_loss = float(np.mean(v_losses))
            self.entropy = float(np.mean(entropies))
            max_ent = math.log(max(2, self.n_actions))
            self.exploration_rate = float(np.clip(self.entropy / max_ent, 0.0, 1.0))
            self.approx_kl = float(np.mean(kls)) if kls else 0.0
            self.clip_fraction = float(np.mean(clips)) if clips else 0.0
        return self.last_loss

    def on_episode_end(self, summary: dict[str, Any]) -> float:
        self.episode += 1
        reward = float(summary.get("reward", 0.0))
        kills = int(summary.get("kills", 0))
        shots = int(summary.get("shots", 0))
        hits = int(summary.get("hits", 0))
        self.total_kills += kills
        self.total_shots += shots
        self.total_hits += hits
        self.accuracy = self.total_hits / max(1, self.total_shots)

        improved_reward = reward > self.best_reward
        self.best_reward = max(self.best_reward, reward)
        if self.total_kills > self.best_kills or improved_reward:
            self.best_kills = max(self.best_kills, self.total_kills)
            self.save_best()

        recent = [h["reward"] for h in self.history[-19:]] + [reward]
        self.avg_reward = float(np.mean(recent)) if recent else reward

        self.history.append(
            {
                "episode": self.episode,
                "env_episode": int(summary.get("episode", self.episode)),
                "reward": round(reward, 3),
                "kills": kills,
                "shots": shots,
                "hits": hits,
                "accuracy": round(float(summary.get("accuracy", 0.0)), 3),
                "steps": int(summary.get("steps", 0)),
                "loss": round(self.last_loss, 4),
                "entropy": round(self.entropy, 4),
                "exploration_rate": round(self.exploration_rate, 3),
            }
        )
        if len(self.history) > 240:
            self.history = self.history[-240:]
        self.save()
        return self.last_loss

    def status(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm_name,
            "scenario_id": self.scenario_id,
            "n_actions": self.n_actions,
            "action_labels": self.action_labels,
            "episodes": self.episode,
            "total_steps": self.total_steps,
            "updates": self.updates,
            "rollout_progress": len(self.buffer),
            "rollout_steps": self.config.rollout_steps,
            "avg_reward": round(self.avg_reward, 3),
            "best_reward": round(0.0 if self.best_reward < -1e8 else self.best_reward, 3),
            "best_kills": self.best_kills,
            "last_loss": round(self.last_loss, 4),
            "policy_loss": round(self.policy_loss, 4),
            "value_loss": round(self.value_loss, 4),
            "entropy": round(self.entropy, 4),
            "exploration_rate": round(self.exploration_rate, 3),
            "approx_kl": round(self.approx_kl, 5),
            "clip_fraction": round(self.clip_fraction, 3),
            "training_enabled": self.training_enabled,
            "greedy": self.greedy,
            "temperature": round(self.temperature, 2),
            "loaded": self.loaded,
            "total_kills": self.total_kills,
            "total_shots": self.total_shots,
            "total_hits": self.total_hits,
            "accuracy": round(self.accuracy, 3),
            "history": self.history[-60:],
        }

    def best_path(self) -> str:
        directory = os.path.dirname(self.save_path) or "."
        base = os.path.splitext(os.path.basename(self.save_path))[0]
        return os.path.join(directory, f"{base}_best.pt")

    def save_best(self) -> None:
        self.save(self.best_path())

    def save(self, path: str | None = None, extra_stats: dict[str, Any] | None = None) -> None:
        target = path or self.save_path
        directory = os.path.dirname(target)
        if directory:
            os.makedirs(directory, exist_ok=True)
        stats: dict[str, Any] = {
            "scenario_id": self.scenario_id,
            "n_actions": self.n_actions,
            "action_labels": self.action_labels,
            "episode": self.episode,
            "total_steps": self.total_steps,
            "updates": self.updates,
            "best_reward": self.best_reward,
            "best_kills": self.best_kills,
            "avg_reward": self.avg_reward,
            "last_loss": self.last_loss,
            "policy_loss": self.policy_loss,
            "value_loss": self.value_loss,
            "entropy": self.entropy,
            "exploration_rate": self.exploration_rate,
            "total_kills": self.total_kills,
            "total_shots": self.total_shots,
            "total_hits": self.total_hits,
            "accuracy": self.accuracy,
        }
        if extra_stats:
            stats.update(extra_stats)
        payload = {
            "state_dict": self.network.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "snn_state": self.snn_state,
            "history": self.history,
            "stats": stats,
        }
        tmp = target + ".tmp"
        torch.save(payload, tmp)
        os.replace(tmp, target)

    def load(self, path: str | None = None) -> bool:
        target = path or self.save_path
        if not os.path.exists(target):
            return False
        try:
            try:
                ckpt = torch.load(target, map_location=self.device, weights_only=False)
            except TypeError:
                ckpt = torch.load(target, map_location=self.device)
            stats = ckpt.get("stats", {})
            saved_n = int(stats.get("n_actions", self.n_actions))
            if saved_n != self.n_actions:
                self.n_actions = saved_n
                self.network = self._build_network(saved_n)
            self.network.load_state_dict(ckpt["state_dict"], strict=False)
            self.optimizer = torch.optim.Adam(
                self.network.parameters(), lr=self.config.lr, eps=1e-5
            )
            opt_state = ckpt.get("optimizer_state_dict")
            if opt_state:
                try:
                    self.optimizer.load_state_dict(opt_state)
                except Exception:
                    pass
            self.snn_state = ckpt.get("snn_state") or {}
            self.history = ckpt.get("history", [])
            self.episode = int(stats.get("episode", 0))
            self.total_steps = int(stats.get("total_steps", 0))
            self.updates = int(stats.get("updates", 0))
            self.best_reward = float(stats.get("best_reward", -1e9))
            self.best_kills = int(stats.get("best_kills", 0))
            self.avg_reward = float(stats.get("avg_reward", 0.0))
            self.last_loss = float(stats.get("last_loss", 0.0))
            self.policy_loss = float(stats.get("policy_loss", 0.0))
            self.value_loss = float(stats.get("value_loss", 0.0))
            self.entropy = float(stats.get("entropy", math.log(max(2, self.n_actions))))
            self.exploration_rate = float(stats.get("exploration_rate", 1.0))
            self.total_kills = int(stats.get("total_kills", 0))
            self.total_shots = int(stats.get("total_shots", 0))
            self.total_hits = int(stats.get("total_hits", 0))
            self.accuracy = float(stats.get("accuracy", 0.0))
            self.loaded = True
            return True
        except Exception as exc:
            print(f"[PPOAgent] No se pudo cargar {target}: {exc}")
            return False

    def reset(self) -> None:
        self.network = self._build_network(self.n_actions)
        self.optimizer = torch.optim.Adam(self.network.parameters(), lr=self.config.lr, eps=1e-5)
        self.buffer.clear()
        self.episode = 0
        self.total_steps = 0
        self.updates = 0
        self.best_reward = -1e9
        self.best_kills = 0
        self.avg_reward = 0.0
        self.total_kills = 0
        self.total_shots = 0
        self.total_hits = 0
        self.accuracy = 0.0
        self.last_loss = 0.0
        self.policy_loss = 0.0
        self.value_loss = 0.0
        self.entropy = math.log(max(2, self.n_actions))
        self.exploration_rate = 1.0
        self.approx_kl = 0.0
        self.clip_fraction = 0.0
        self.snn_state = {}
        self.history.clear()
        self.loaded = False
        self.save()
