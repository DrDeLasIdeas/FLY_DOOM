import os
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


ACTION_LABELS = ["TURN_LEFT", "TURN_RIGHT", "ATTACK", "IDLE"]
RETINA_POOL = 8
RETINA_DIM = RETINA_POOL * RETINA_POOL
DN_DIM = 4
ENEMY_DIM = 4
FEATURE_DIM = RETINA_DIM + DN_DIM + ENEMY_DIM


class MotorPolicy(nn.Module):
    """Readout motor descendente entrenable sobre la actividad del conectoma.

    Convierte la retina 64x64, las tasas de las neuronas descendentes (DNs) y la
    posición retinotópica de la amenaza en una distribución de acciones
    (izquierda, derecha, disparar, reposo). Se entrena localmente por imitación
    de un reflejo visual y se refina en vivo con REINFORCE modulado por recompensa.
    """

    def __init__(self, feature_dim: int = FEATURE_DIM, hidden_dim: int = 64,
                 n_actions: int = len(ACTION_LABELS), save_path: str = "data/motor_policy.pt"):
        super().__init__()
        self.feature_dim = feature_dim
        self.n_actions = n_actions
        self.save_path = save_path
        self.net = nn.Sequential(
            nn.Linear(feature_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, n_actions),
        )
        self.value_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )
        self.optimizer = torch.optim.Adam(self.parameters(), lr=1e-3)
        self.gamma = 0.99
        self.entropy_coef = 0.012
        self.value_coef = 0.5
        self.temperature = 1.0
        self.training_enabled = True
        self.greedy = False
        self.loaded = False
        self.episode = 0
        self.total_steps = 0
        self.best_reward = -1e9
        self.best_kills = 0
        self.avg_reward = 0.0
        self.last_loss = 0.0
        self.total_kills = 0
        self.total_shots = 0
        self.total_hits = 0
        self.accuracy = 0.0
        self.history: list[dict] = []
        self.snn_state: dict = {}
        self.log_probs: list[torch.Tensor] = []
        self.rewards: list[float] = []
        self.entropies: list[torch.Tensor] = []
        self.values: list[torch.Tensor] = []

    def build_features(self, retina_64: np.ndarray, dn_rates: dict, enemy: dict) -> np.ndarray:
        img = np.asarray(retina_64, dtype=np.float32)
        if img.ndim == 3:
            img = img.mean(axis=2)
        if img.shape != (64, 64):
            ys = np.linspace(0, img.shape[0] - 1, 64).astype(int)
            xs = np.linspace(0, img.shape[1] - 1, 64).astype(int)
            img = img[np.ix_(ys, xs)]
        pooled = (img / 255.0).reshape(RETINA_POOL, 8, RETINA_POOL, 8).mean(axis=(1, 3)).flatten()
        dn = np.array(
            [
                dn_rates.get("dn_left", 0.0),
                dn_rates.get("dn_right", 0.0),
                dn_rates.get("dn_move", 0.0),
                dn_rates.get("dn_attack", 0.0),
            ],
            dtype=np.float32,
        )
        dn = np.clip(dn * 8.0, 0.0, 4.0)
        enemy_feat = np.array(
            [
                float(enemy.get("present", 0.0)),
                float(np.clip(enemy.get("offset", 0.0), -1.0, 1.0)),
                float(np.clip(enemy.get("size", 0.0) * 20.0, 0.0, 1.0)),
                float(enemy.get("centered", 0.0)),
            ],
            dtype=np.float32,
        )
        return np.concatenate([pooled, dn, enemy_feat]).astype(np.float32)

    def act(self, features: np.ndarray, greedy: bool | None = None):
        greedy = self.greedy if greedy is None else greedy
        x = torch.as_tensor(features, dtype=torch.float32).unsqueeze(0)
        hidden = self.net[:4](x)
        logits = self.net[4](hidden)
        value = self.value_head(hidden).squeeze(-1)
        probs = F.softmax(logits / max(0.2, self.temperature), dim=-1)
        if greedy:
            action_t = torch.argmax(probs, dim=-1)
            log_prob = torch.log(probs[0, action_t.item()] + 1e-8)
            entropy = -(probs * torch.log(probs + 1e-8)).sum()
        else:
            dist = torch.distributions.Categorical(probs=probs)
            action_t = dist.sample()
            log_prob = dist.log_prob(action_t)
            entropy = dist.entropy()
        action = int(action_t.item())
        if self.training_enabled:
            self.log_probs.append(log_prob)
            self.entropies.append(entropy)
            self.values.append(value.squeeze(0))
        self.total_steps += 1
        return action, float(probs[0, action].item()), [float(p) for p in probs[0].detach().tolist()]

    def observe_reward(self, reward: float):
        if self.training_enabled:
            self.rewards.append(float(reward))

    def finish_episode(self, summary: dict) -> float:
        loss_value = 0.0
        n = min(len(self.log_probs), len(self.rewards))
        if self.training_enabled and n > 1:
            returns = []
            running = 0.0
            for reward in reversed(self.rewards[:n]):
                running = reward + self.gamma * running
                returns.append(running)
            returns.reverse()
            ret = torch.tensor(returns, dtype=torch.float32)
            ret = (ret - ret.mean()) / (ret.std() + 1e-8)
            log_probs = torch.stack(self.log_probs[:n])
            entropies = torch.stack(self.entropies[:n])
            values = torch.stack(self.values[:n])
            advantages = ret - values.detach()
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
            policy_loss = -(log_probs * advantages).mean() - self.entropy_coef * entropies.mean()
            value_loss = F.mse_loss(values, ret)
            loss = policy_loss + self.value_coef * value_loss
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.parameters(), 1.0)
            self.optimizer.step()
            loss_value = float(loss.item())
            self.last_loss = loss_value

        self.log_probs.clear()
        self.rewards.clear()
        self.entropies.clear()
        self.values.clear()
        self.episode += 1

        reward = float(summary.get("reward", 0.0))
        kills = int(summary.get("kills", 0))
        shots = int(summary.get("shots", 0))
        hits = int(summary.get("hits", 0))
        self.total_kills += kills
        self.total_shots += shots
        self.total_hits += hits
        self.accuracy = self.total_hits / max(1, self.total_shots)
        self.best_reward = max(self.best_reward, reward)
        if self.total_kills > self.best_kills:
            self.best_kills = self.total_kills
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
                "loss": round(loss_value, 4),
            }
        )
        if len(self.history) > 240:
            self.history = self.history[-240:]
        self.save()
        return loss_value

    def train_supervised(self, features, actions, epochs: int = 20, batch_size: int = 64,
                         lr: float = 1e-3) -> list[float]:
        X = torch.as_tensor(np.asarray(features), dtype=torch.float32)
        Y = torch.as_tensor(np.asarray(actions), dtype=torch.long)
        self.optimizer = torch.optim.Adam(self.parameters(), lr=lr)
        losses: list[float] = []
        for _ in range(max(1, epochs)):
            perm = torch.randperm(len(X))
            total = 0.0
            for start in range(0, len(X), batch_size):
                idx = perm[start:start + batch_size]
                logits = self.net(X[idx])
                loss = F.cross_entropy(logits, Y[idx])
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
                total += float(loss.item()) * len(idx)
            losses.append(total / max(1, len(X)))
        self.last_loss = losses[-1] if losses else 0.0
        return losses

    def status(self) -> dict:
        return {
            "episodes": self.episode,
            "total_steps": self.total_steps,
            "avg_reward": round(self.avg_reward, 3),
            "best_reward": round(self.best_reward, 3),
            "best_kills": self.best_kills,
            "last_loss": round(self.last_loss, 4),
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
        return os.path.join(directory, "motor_policy_best.pt")

    def save_best(self):
        self.save(self.best_path())

    def save(self, path: str | None = None, extra_stats: dict | None = None):
        target = path or self.save_path
        directory = os.path.dirname(target)
        if directory:
            os.makedirs(directory, exist_ok=True)
        stats = {
            "episode": self.episode,
            "total_steps": self.total_steps,
            "best_reward": self.best_reward,
            "best_kills": self.best_kills,
            "avg_reward": self.avg_reward,
            "last_loss": self.last_loss,
            "total_kills": self.total_kills,
            "total_shots": self.total_shots,
            "total_hits": self.total_hits,
            "accuracy": self.accuracy,
        }
        if extra_stats:
            stats.update(extra_stats)
        payload = {
            "state_dict": self.state_dict(),
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
                ckpt = torch.load(target, map_location="cpu", weights_only=False)
            except TypeError:
                ckpt = torch.load(target, map_location="cpu")
            self.load_state_dict(ckpt["state_dict"], strict=False)
            self.optimizer = torch.optim.Adam(self.parameters(), lr=1e-3)
            opt_state = ckpt.get("optimizer_state_dict")
            if opt_state:
                try:
                    self.optimizer.load_state_dict(opt_state)
                except Exception:
                    pass
            self.snn_state = ckpt.get("snn_state") or {}
            self.history = ckpt.get("history", [])
            stats = ckpt.get("stats", {})
            self.episode = int(stats.get("episode", 0))
            self.total_steps = int(stats.get("total_steps", 0))
            self.best_reward = float(stats.get("best_reward", -1e9))
            self.best_kills = int(stats.get("best_kills", 0))
            self.avg_reward = float(stats.get("avg_reward", 0.0))
            self.last_loss = float(stats.get("last_loss", 0.0))
            self.total_kills = int(stats.get("total_kills", 0))
            self.total_shots = int(stats.get("total_shots", 0))
            self.total_hits = int(stats.get("total_hits", 0))
            self.accuracy = float(stats.get("accuracy", 0.0))
            self.loaded = True
            return True
        except Exception as exc:
            print(f"[MotorPolicy] No se pudo cargar {target}: {exc}")
            return False

    def reset(self):
        for module in list(self.net) + list(self.value_head):
            if hasattr(module, "reset_parameters"):
                module.reset_parameters()
        self.optimizer = torch.optim.Adam(self.parameters(), lr=1e-3)
        self.episode = 0
        self.total_steps = 0
        self.best_reward = -1e9
        self.best_kills = 0
        self.avg_reward = 0.0
        self.last_loss = 0.0
        self.total_kills = 0
        self.total_shots = 0
        self.total_hits = 0
        self.accuracy = 0.0
        self.snn_state = {}
        self.history.clear()
        self.log_probs.clear()
        self.rewards.clear()
        self.entropies.clear()
        self.values.clear()
        self.loaded = False
        self.save()
