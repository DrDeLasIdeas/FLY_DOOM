"""Entrena localmente la política motora descendente del conectoma de Drosophila.

Flujo (preset `fast` por defecto):
  0. Warmup sintético — calienta el conectoma y la política en la Cyber-Arena.
  1. Imitación — un reflejo visual genera pares (actividad del conectoma, acción)
     y se preentrena la política por entropía cruzada.
  2. REINFORCE + A2C-lite — la política juega en ViZDoom nativo (o sintético) y
     se refina con recompensa moldeada, cabeza de valor y currículo de dificultad.
  3. Evaluación greedy opcional y checkpoint best-by-kills.

Uso:
    PYTHONPATH=. .venv311/bin/python scripts/train_motor_policy.py --preset fast
    PYTHONPATH=. .venv311/bin/python scripts/train_motor_policy.py --preset full --target-kills 100
    PYTHONPATH=. .venv311/bin/python scripts/train_motor_policy.py --episodes 20 --force-synthetic
"""

import argparse
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.connectome_snn import DrosophilaConnectomeEngine
from backend.app.doom_bridge import DoomFlyEnvironment
from backend.app.motor_policy import ACTION_LABELS, MotorPolicy


INITIAL_RATES = {
    "dn_left": 0.01,
    "dn_right": 0.01,
    "dn_move": 0.01,
    "dn_attack": 0.01,
}

PRESETS = {
    "bootstrap": dict(
        imitation_steps=600, epochs=8, episodes=8, max_episodes=20, tic_skip=2,
        substeps=1, target_kills=20, warmup_steps=300, skill=1,
        skill_curriculum=False, native=False,
    ),
    "fast": dict(
        imitation_steps=800, epochs=10, episodes=0, max_episodes=200, tic_skip=2,
        substeps=1, target_kills=100, warmup_steps=400, skill=1,
        skill_curriculum=True, native=True,
    ),
    "standard": dict(
        imitation_steps=2000, epochs=15, episodes=0, max_episodes=150, tic_skip=3,
        substeps=2, target_kills=100, warmup_steps=600, skill=3,
        skill_curriculum=True, native=True,
    ),
    "full": dict(
        imitation_steps=3000, epochs=20, episodes=0, max_episodes=120, tic_skip=4,
        substeps=4, target_kills=150, warmup_steps=800, skill=3,
        skill_curriculum=True, native=True,
    ),
}

CURRICULUM = (1, 3, 5)


def teacher_action(enemy: dict, ammo: float, rng: np.random.Generator) -> int:
    if enemy["present"] < 0.5:
        return 3 if rng.random() < 0.75 else int(rng.integers(0, 2))
    offset = enemy["offset"]
    if abs(offset) > 0.12:
        return 0 if offset < 0 else 1
    if ammo > 0:
        return 2
    return 3


def make_env(force_synthetic: bool, skill: int) -> DoomFlyEnvironment:
    return DoomFlyEnvironment(
        force_synthetic=force_synthetic,
        encode_frames=False,
        render_overlay=False,
        skill=skill,
    )


def prime_env(env: DoomFlyEnvironment) -> tuple[np.ndarray, float]:
    for _ in range(12):
        probe = env.step(action_idx=3)
        if not probe["episode_finished"]:
            return probe["retina_64"], probe["bio_reward"]
    return np.zeros((64, 64), dtype=np.uint8), 0.0


def step_snn(snn, retina, reward, substeps):
    rates = dict(INITIAL_RATES)
    for _ in range(max(1, substeps)):
        rates = snn.step_biophysics(retina, reward, dt=1.0)
        reward = 0.0
    return rates


def collect_imitation(env, snn, policy, steps, tic_skip, substeps, seed=7):
    rng = np.random.default_rng(seed)
    env.set_tic_skip(tic_skip)
    features: list[np.ndarray] = []
    actions: list[int] = []
    last_retina, last_reward = prime_env(env)
    t0 = time.time()

    for i in range(steps):
        rates = step_snn(snn, last_retina, last_reward, substeps)
        last_reward = 0.0
        enemy = env.enemy_state_snapshot()
        feats = policy.build_features(last_retina, rates, enemy)
        action = teacher_action(enemy, env.last_ammo, rng)
        result = env.step(action_idx=action)
        last_retina = result["retina_64"]
        last_reward = 0.0 if result["episode_finished"] else result["bio_reward"]

        if result["episode_finished"]:
            continue

        features.append(feats)
        actions.append(action)

        if (i + 1) % 500 == 0:
            elapsed = max(1e-6, time.time() - t0)
            print(
                f"  imitación {i + 1}/{steps} | {len(features)} muestras | "
                f"{len(features) / elapsed:5.1f} muestras/s | "
                f"enemigo={result['enemy']['present']:.0f} | "
                f"acción={ACTION_LABELS[action]} | recompensa={result['shaped_reward']:+.3f}"
            )

    return (
        np.asarray(features, dtype=np.float32),
        np.asarray(actions, dtype=np.int64),
    )


def run_episode(env, snn, policy, tic_skip, substeps, train=True):
    env.set_tic_skip(tic_skip)
    last_retina, last_reward = prime_env(env)
    steps = 0
    while True:
        rates = step_snn(snn, last_retina, last_reward, substeps)
        last_reward = 0.0
        feats = policy.build_features(last_retina, rates, env.enemy_state_snapshot())
        action, _, _ = policy.act(feats)
        result = env.step(action_idx=action)
        last_retina = result["retina_64"]
        last_reward = 0.0

        if result["episode_finished"]:
            summary = result["last_episode"]
            loss = policy.finish_episode(summary) if train else 0.0
            return summary, loss
        if train:
            policy.observe_reward(result["shaped_reward"])
        steps += 1


def train_reinforce(env_factory, snn, policy, tic_skip, substeps, episodes,
                    target_kills, max_episodes, skills):
    skills = list(skills)
    n_skills = max(1, len(skills))
    per_skill_kills = (target_kills / n_skills) if target_kills > 0 else 0.0
    per_skill_episodes = (episodes / n_skills) if episodes > 0 else 0
    per_skill_max_episodes = (max_episodes / n_skills) if max_episodes > 0 else 0
    start_kills = policy.total_kills
    session_kills = 0
    episodes_run = 0
    t0 = time.time()

    for skill in skills:
        if target_kills > 0 and session_kills >= target_kills:
            break
        if episodes > 0 and episodes_run >= episodes:
            break
        if max_episodes > 0 and episodes_run >= max_episodes:
            break

        env = env_factory(skill)
        mode = "SYNTHETIC_ARENA" if env.use_synthetic else "VIZDOOM_NATIVE"
        print(f"\n[Fase 2] REINFORCE | skill={skill} | arena={mode}")
        policy.training_enabled = True
        policy.greedy = False
        policy.temperature = 1.0
        policy.log_probs.clear()
        policy.rewards.clear()
        policy.entropies.clear()
        policy.values.clear()

        skill_kills = 0
        skill_episodes = 0
        while True:
            if per_skill_kills > 0 and skill_kills >= per_skill_kills:
                break
            if per_skill_episodes > 0 and skill_episodes >= per_skill_episodes:
                break
            if per_skill_max_episodes > 0 and skill_episodes >= per_skill_max_episodes:
                break
            if target_kills > 0 and session_kills >= target_kills:
                break
            if episodes > 0 and episodes_run >= episodes:
                break
            if max_episodes > 0 and episodes_run >= max_episodes:
                break

            summary, loss = run_episode(env, snn, policy, tic_skip, substeps, train=True)
            skill_kills += summary["kills"]
            skill_episodes += 1
            session_kills += summary["kills"]
            episodes_run += 1
            elapsed = max(1e-6, time.time() - t0)
            print(
                f"  ep {episodes_run:03d} (skill {skill}) | recompensa={summary['reward']:+.2f} | "
                f"bajas={summary['kills']} | disparos={summary['shots']} | "
                f"efectividad={summary['accuracy']:.2f} | pasos={summary['steps']} | "
                f"loss={loss:.4f} | sesión={session_kills} bajas | {episodes_run / elapsed:.2f} ep/s"
            )

        env.close()

    return session_kills, episodes_run, start_kills


def evaluate(env_factory, snn, policy, tic_skip, substeps, episodes, skill):
    env = env_factory(skill)
    print(f"\n[Fase 3] Evaluación greedy ({episodes} episodios, skill={skill})")
    prev_training, prev_greedy = policy.training_enabled, policy.greedy
    policy.training_enabled = False
    policy.greedy = True
    total_kills = total_shots = 0
    for ep in range(1, episodes + 1):
        summary, _ = run_episode(env, snn, policy, tic_skip, substeps, train=False)
        total_kills += summary["kills"]
        total_shots += summary["shots"]
        print(
            f"  eval {ep}/{episodes} | bajas={summary['kills']} | disparos={summary['shots']} | "
            f"efectividad={summary['accuracy']:.2f} | recompensa={summary['reward']:+.2f}"
        )
    policy.training_enabled = prev_training
    policy.greedy = prev_greedy
    env.close()
    acc = total_kills / max(1, total_shots)
    print(f"  Eval total: bajas={total_kills} disparos={total_shots} efectividad={acc:.3f}")
    return total_kills, total_shots


def build_args():
    parser = argparse.ArgumentParser(description="Entrena la política motora de NeuroDoom OS")
    parser.add_argument("--preset", choices=sorted(PRESETS), default="fast")
    parser.add_argument("--imitation-steps", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--episodes", type=int, default=None,
                        help="Episodios RL (0 = hasta alcanzar --target-kills)")
    parser.add_argument("--max-episodes", type=int, default=None)
    parser.add_argument("--tic-skip", type=int, default=None)
    parser.add_argument("--substeps", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--checkpoint", type=str, default="data/motor_policy.pt")
    parser.add_argument("--init-from", type=str, default="data/motor_policy.pt")
    parser.add_argument("--target-kills", type=int, default=None,
                        help="Bajas nuevas en esta sesión antes de detenerse")
    parser.add_argument("--warmup-steps", type=int, default=None)
    parser.add_argument("--skill", type=int, default=None)
    parser.add_argument("--skill-curriculum", action="store_true", default=None)
    parser.add_argument("--eval-episodes", type=int, default=0)
    parser.add_argument("--force-synthetic", action="store_true")
    parser.add_argument("--auto", action="store_true",
                        help="Alias de --episodes 0 (entrenar hasta el objetivo)")
    parser.add_argument("--skip-imitation", action="store_true")
    parser.add_argument("--skip-reinforce", action="store_true")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    preset = PRESETS[args.preset]
    for key, value in preset.items():
        if getattr(args, key, None) is None:
            setattr(args, key, value)
    if args.auto:
        args.episodes = 0
    if args.episodes is None:
        args.episodes = 0
    return args


def main():
    args = build_args()

    print("=" * 78)
    print(f" NeuroDoom OS — Entrenamiento de la política motora (preset={args.preset})")
    print("=" * 78)

    policy = MotorPolicy(save_path=args.checkpoint)
    if args.reset:
        policy.reset()
        print("Política reiniciada desde cero.")
    elif os.path.exists(args.checkpoint) and policy.load():
        print(f"Checkpoint cargado: {args.checkpoint} (episodios={policy.episode}, "
              f"bajas={policy.total_kills})")
    elif args.init_from and os.path.exists(args.init_from) and policy.load(args.init_from):
        print(f"Inicializado desde {args.init_from} (episodios={policy.episode}, "
              f"bajas={policy.total_kills}); se guardará en {args.checkpoint}")
    else:
        print("Sin checkpoint previo: se parte de una política aleatoria.")

    print(f"Cargando conectoma de Drosophila (tic_skip={args.tic_skip}, "
          f"substeps={args.substeps}, objetivo={args.target_kills} bajas)...")
    snn = DrosophilaConnectomeEngine()

    use_synthetic_only = args.force_synthetic or not args.native

    def env_factory(skill):
        return make_env(force_synthetic=use_synthetic_only, skill=skill)

    try:
        if not args.skip_imitation:
            print(f"\n[Fase 0] Warmup sintético ({args.warmup_steps} pasos)")
            warm_env = make_env(force_synthetic=True, skill=1)
            warm_env.set_tic_skip(args.tic_skip)
            collect_imitation(warm_env, snn, policy, args.warmup_steps,
                              args.tic_skip, args.substeps, seed=args.seed)
            warm_env.close()

            print(f"\n[Fase 1] Imitación visual ({args.imitation_steps} pasos)")
            imit_env = make_env(force_synthetic=True, skill=1)
            features, actions = collect_imitation(
                imit_env, snn, policy, args.imitation_steps,
                args.tic_skip, args.substeps, seed=args.seed,
            )
            imit_env.close()
            if len(features) == 0:
                print("No se recolectaron muestras; se omite la fase de imitación.")
            else:
                counts = np.bincount(actions, minlength=len(ACTION_LABELS))
                print(
                    "  Distribución de acciones: "
                    + ", ".join(
                        f"{ACTION_LABELS[i]}={counts[i]}" for i in range(len(ACTION_LABELS))
                    )
                )
                print(f"  Ajuste supervisado ({args.epochs} épocas, lr={args.lr})...")
                losses = policy.train_supervised(
                    features, actions, epochs=args.epochs,
                    batch_size=args.batch_size, lr=args.lr,
                )
                print(f"  Pérdida CE: inicial={losses[0]:.4f} final={losses[-1]:.4f}")
                policy.save()
                print(f"  Checkpoint guardado en {args.checkpoint}")

        if not args.skip_reinforce:
            skills = CURRICULUM if args.skill_curriculum else (args.skill,)
            session_kills, episodes_run, start_kills = train_reinforce(
                env_factory, snn, policy, args.tic_skip, args.substeps,
                args.episodes, args.target_kills, args.max_episodes, skills,
            )
            print(
                f"\n  RL terminado: {episodes_run} episodios | "
                f"{session_kills} bajas nuevas | total acumulado={policy.total_kills} "
                f"(inicio={start_kills})"
            )
            policy.save()

        if args.eval_episodes > 0:
            evaluate(env_factory, snn, policy, args.tic_skip, args.substeps,
                     args.eval_episodes, args.skill)

        status = policy.status()
        print("\n" + "=" * 78)
        print(" Resumen de entrenamiento")
        print("=" * 78)
        print(f"  Episodios RL:     {status['episodes']}")
        print(f"  Pasos totales:    {status['total_steps']}")
        print(f"  Recompensa media: {status['avg_reward']:+.3f}")
        print(f"  Mejor recompensa: {status['best_reward']:+.3f}")
        print(f"  Bajas totales:    {status['total_kills']}")
        print(f"  Disparos totales: {status['total_shots']}")
        print(f"  Efectividad:      {status['accuracy']:.3f}")
        print(f"  Checkpoint:       {args.checkpoint}")
        print(f"  Best-by-kills:    {policy.best_path()}")
        print("=" * 78)
    except KeyboardInterrupt:
        print("\nEntrenamiento interrumpido; guardando checkpoint parcial...")
        policy.save()


if __name__ == "__main__":
    main()
