"""Entrenador CLI PPO-CNN Multi-Escenario sobre ViZDoom (PyTorch puro).

Pipeline del Buffer Visual:
  RGB24 (320x240) -> Grayscale -> Resize (84x84) -> Normalización [0, 1] -> FrameStack (4, 84, 84)

Ejemplos:
  PYTHONPATH=. .venv311/bin/python scripts/train_ppo.py --scenario defend_the_center --episodes 50
  PYTHONPATH=. .venv311/bin/python scripts/train_ppo.py --scenario basic --episodes 30
  PYTHONPATH=. .venv311/bin/python scripts/train_ppo.py --scenario health_gathering --episodes 40 --force-synthetic
  PYTHONPATH=. .venv311/bin/python scripts/train_ppo.py --all-scenarios --episodes 20
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.rl import PPOAgent, PPOConfig
from backend.app.scenarios import ScenarioFactory
from backend.app.vision import VisualBufferConfig, VisualBufferProcessor


def train_scenario(
    scenario_id: str,
    *,
    episodes: int,
    tic_skip: int,
    skill: int | None,
    force_synthetic: bool,
    rollout_steps: int,
    lr: float,
    checkpoint_dir: str,
    reset: bool,
) -> dict:
    factory = ScenarioFactory()
    env = factory.create(
        scenario_id=scenario_id,
        force_synthetic=force_synthetic,
        skill=skill,
        tic_skip=tic_skip,
        render_overlay=False,
    )
    processor = VisualBufferProcessor(VisualBufferConfig(width=84, height=84, stack_size=4))
    cfg = PPOConfig(
        lr=lr,
        rollout_steps=rollout_steps,
        checkpoint_dir=checkpoint_dir,
    )
    agent = PPOAgent(
        scenario_id=scenario_id,
        action_labels=env.action_labels,
        config=cfg,
    )
    if reset:
        agent.reset()
    elif os.path.exists(agent.save_path):
        agent.load()

    print("=" * 78)
    print(f" NeuroDoom OS — PPO-CNN Trainer | escenario={scenario_id} | modo={env.mode}")
    print(f" Acciones ({len(env.action_labels)}): {', '.join(env.action_labels)}")
    print("=" * 78)

    t0 = time.time()
    try:
        for ep in range(1, episodes + 1):
            processor.reset()
            first = env.reset()
            obs = processor.process(first.raw_frame)

            while True:
                decision = agent.select_action(obs, env.action_labels)
                step_obs = env.step(decision.action_idx, decision.action_name)

                if step_obs.episode_finished:
                    agent.observe_transition(
                        obs,
                        decision,
                        step_obs.shaped_reward,
                        True,
                        next_obs=obs,
                    )
                    agent.on_episode_end(step_obs.last_episode)
                    st = agent.status()
                    elapsed = max(1e-6, time.time() - t0)
                    print(
                        f"  ep {ep:03d}/{episodes:03d} | "
                        f"reward={step_obs.last_episode['reward']:+6.2f} | "
                        f"avg={st['avg_reward']:+6.2f} | "
                        f"kills={step_obs.last_episode['kills']:2d} | "
                        f"loss={st['last_loss']:.4f} | "
                        f"expl={st['exploration_rate']:.2f} | "
                        f"updates={st['updates']} | "
                        f"{st['total_steps'] / elapsed:5.1f} fps"
                    )
                    break

                next_obs = processor.process(step_obs.raw_frame)
                agent.observe_transition(
                    obs,
                    decision,
                    step_obs.shaped_reward,
                    False,
                    next_obs=next_obs,
                )
                obs = next_obs

        agent.save()
    except KeyboardInterrupt:
        print("\nEntrenamiento interrumpido; guardando checkpoint PPO...")
        agent.save()
    finally:
        env.close()

    return agent.status()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Entrenamiento PPO-CNN multi-escenario en ViZDoom")
    parser.add_argument("--scenario", type=str, default="defend_the_center")
    parser.add_argument("--all-scenarios", action="store_true")
    parser.add_argument("--episodes", type=int, default=30)
    parser.add_argument("--tic-skip", type=int, default=2)
    parser.add_argument("--skill", type=int, default=None)
    parser.add_argument("--rollout-steps", type=int, default=128)
    parser.add_argument("--lr", type=float, default=2.5e-4)
    parser.add_argument("--checkpoint-dir", type=str, default="checkpoints")
    parser.add_argument("--force-synthetic", action="store_true")
    parser.add_argument("--reset", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    factory = ScenarioFactory()
    targets = factory.registry.list_ids() if args.all_scenarios else [args.scenario]
    for scenario_id in targets:
        train_scenario(
            scenario_id,
            episodes=args.episodes,
            tic_skip=args.tic_skip,
            skill=args.skill,
            force_synthetic=args.force_synthetic,
            rollout_steps=args.rollout_steps,
            lr=args.lr,
            checkpoint_dir=args.checkpoint_dir,
            reset=args.reset,
        )


if __name__ == "__main__":
    main()
