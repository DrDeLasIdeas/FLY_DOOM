"""On-policy Rollout Buffer with Generalized Advantage Estimation (GAE)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import numpy as np
import torch


@dataclass
class RolloutBatch:
    obs: torch.Tensor
    actions: torch.Tensor
    old_log_probs: torch.Tensor
    advantages: torch.Tensor
    returns: torch.Tensor
    old_values: torch.Tensor


class RolloutBuffer:
    """Stores on-policy trajectories and computes GAE advantages for PPO updates."""

    def __init__(self):
        self.observations: list[np.ndarray] = []
        self.actions: list[int] = []
        self.log_probs: list[float] = []
        self.rewards: list[float] = []
        self.dones: list[bool] = []
        self.values: list[float] = []

    def __len__(self) -> int:
        return len(self.observations)

    def clear(self) -> None:
        self.observations.clear()
        self.actions.clear()
        self.log_probs.clear()
        self.rewards.clear()
        self.dones.clear()
        self.values.clear()

    def pop_snapshot(self) -> "RolloutBuffer":
        """Extracts a detached copy of the current trajectory and clears this buffer."""
        snap = RolloutBuffer()
        snap.observations = list(self.observations)
        snap.actions = list(self.actions)
        snap.log_probs = list(self.log_probs)
        snap.rewards = list(self.rewards)
        snap.dones = list(self.dones)
        snap.values = list(self.values)
        self.clear()
        return snap

    def add(
        self,
        obs: np.ndarray,
        action: int,
        log_prob: float,
        reward: float,
        done: bool,
        value: float,
    ) -> None:
        self.observations.append(np.asarray(obs, dtype=np.float32))
        self.actions.append(int(action))
        self.log_probs.append(float(log_prob))
        self.rewards.append(float(reward))
        self.dones.append(bool(done))
        self.values.append(float(value))

    def compute_gae(
        self,
        last_value: float,
        last_done: bool,
        *,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
    ) -> tuple[np.ndarray, np.ndarray]:
        n = len(self.rewards)
        advantages = np.zeros(n, dtype=np.float32)
        last_gae = 0.0
        for step in reversed(range(n)):
            if step == n - 1:
                next_non_terminal = 0.0 if last_done else 1.0
                next_value = float(last_value)
            else:
                next_non_terminal = 0.0 if self.dones[step] else 1.0
                next_value = self.values[step + 1]
            delta = (
                self.rewards[step]
                + gamma * next_value * next_non_terminal
                - self.values[step]
            )
            last_gae = delta + gamma * gae_lambda * next_non_terminal * last_gae
            advantages[step] = last_gae

        returns = advantages + np.asarray(self.values, dtype=np.float32)
        return advantages, returns

    def iter_minibatches(
        self,
        advantages: np.ndarray,
        returns: np.ndarray,
        *,
        minibatch_size: int = 32,
        device: torch.device | str = "cpu",
    ) -> Iterator[RolloutBatch]:
        n = len(self.observations)
        if n == 0:
            return
        obs_t = torch.as_tensor(np.stack(self.observations, axis=0), dtype=torch.float32, device=device)
        act_t = torch.as_tensor(self.actions, dtype=torch.long, device=device)
        logp_t = torch.as_tensor(self.log_probs, dtype=torch.float32, device=device)
        adv_t = torch.as_tensor(advantages, dtype=torch.float32, device=device)
        ret_t = torch.as_tensor(returns, dtype=torch.float32, device=device)
        val_t = torch.as_tensor(self.values, dtype=torch.float32, device=device)

        if n > 1:
            adv_t = (adv_t - adv_t.mean()) / (adv_t.std(unbiased=False) + 1e-8)

        indices = np.random.permutation(n)
        batch_sz = max(1, min(int(minibatch_size), n))
        for start in range(0, n, batch_sz):
            idx = indices[start : start + batch_sz]
            yield RolloutBatch(
                obs=obs_t[idx],
                actions=act_t[idx],
                old_log_probs=logp_t[idx],
                advantages=adv_t[idx],
                returns=ret_t[idx],
                old_values=val_t[idx],
            )
