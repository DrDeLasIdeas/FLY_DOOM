"""Convolutional Actor-Critic neural network for stacked ViZDoom visual buffers."""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical


def _layer_init(layer: nn.Module, std: float = np.sqrt(2.0), bias_const: float = 0.0) -> nn.Module:
    if hasattr(layer, "weight") and layer.weight is not None:
        nn.init.orthogonal_(layer.weight, std)
    if hasattr(layer, "bias") and layer.bias is not None:
        nn.init.constant_(layer.bias, bias_const)
    return layer


class ActorCriticCNN(nn.Module):
    """Nature-DQN convolutional backbone shared by Actor (policy) and Critic (value).

    Expects float32 visual buffer tensors of shape (B, stack_size, H, W) normalized in [0, 1].
    """

    def __init__(
        self,
        in_channels: int = 4,
        n_actions: int = 4,
        obs_height: int = 84,
        obs_width: int = 84,
        hidden_dim: int = 256,
    ):
        super().__init__()
        self.in_channels = in_channels
        self.n_actions = n_actions
        self.obs_height = obs_height
        self.obs_width = obs_width

        self.encoder = nn.Sequential(
            _layer_init(nn.Conv2d(in_channels, 32, kernel_size=8, stride=4)),
            nn.ReLU(),
            _layer_init(nn.Conv2d(32, 64, kernel_size=4, stride=2)),
            nn.ReLU(),
            _layer_init(nn.Conv2d(64, 64, kernel_size=3, stride=1)),
            nn.ReLU(),
            nn.Flatten(),
        )

        with torch.no_grad():
            dummy = torch.zeros(1, in_channels, obs_height, obs_width)
            flat_dim = int(self.encoder(dummy).shape[1])

        self.fc = nn.Sequential(
            _layer_init(nn.Linear(flat_dim, hidden_dim)),
            nn.ReLU(),
        )
        self.actor_head = _layer_init(nn.Linear(hidden_dim, n_actions), std=0.01)
        self.critic_head = _layer_init(nn.Linear(hidden_dim, 1), std=1.0)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        features = self.fc(self.encoder(x))
        logits = self.actor_head(features)
        value = self.critic_head(features).squeeze(-1)
        return logits, value

    def evaluate_actions(
        self, x: torch.Tensor, actions: torch.Tensor, temperature: float = 1.0
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        logits, values = self.forward(x)
        scaled = logits / max(0.2, float(temperature))
        dist = Categorical(logits=scaled)
        return dist.log_prob(actions), dist.entropy(), values

    @torch.no_grad()
    def act(
        self,
        obs: np.ndarray,
        *,
        temperature: float = 1.0,
        greedy: bool = False,
        device: torch.device | str = "cpu",
    ) -> tuple[int, float, list[float], float, float, float]:
        x = torch.as_tensor(obs, dtype=torch.float32, device=device).unsqueeze(0)
        logits, value = self.forward(x)
        scaled = logits / max(0.2, float(temperature))
        probs = F.softmax(scaled, dim=-1)
        dist = Categorical(probs=probs)

        if greedy:
            action_t = torch.argmax(probs, dim=-1)
            log_prob = torch.log(probs[0, action_t.item()] + 1e-8)
            entropy = dist.entropy()
        else:
            action_t = dist.sample()
            log_prob = dist.log_prob(action_t)
            entropy = dist.entropy()

        action_idx = int(action_t.item())
        probs_list = [float(p) for p in probs[0].cpu().tolist()]
        return (
            action_idx,
            float(probs_list[action_idx]),
            probs_list,
            float(value.item()),
            float(log_prob.item()),
            float(entropy.item()),
        )
