# Plan Técnico — Spec 002 Refactorización SOLID + PPO Visual

## Estructura modular (Backend `backend/app/`)
1. `core/interfaces.py`: Contratos abstractos (`VisualPreprocessor`, `EnvironmentAdapter`, `RLAgent`, `RewardShaper`, `Neuromodulator`) y dataclasses (`ScenarioConfig`, `StepObservation`, `ActionDecision`).
2. `vision/preprocessor.py`: `VisualBufferProcessor` (RGB -> Grayscale -> 84x84 -> `[0,1]` -> `FrameStack(k=4)` + mosaico visual Base64 + retina 64x64 para SNN).
3. `scenarios/`:
   - `configs/*.json`: Definiciones declarativas para `defend_the_center`, `basic`, `deadly_corridor`, `health_gathering`, `defend_the_line`.
   - `registry.py`: Registro dinámico de escenarios desde JSON.
   - `reward_shaper.py`: Estrategias intercambiables de *reward shaping* (`BasicRewardShaper`, `CombatRewardShaper`, `NavigationRewardShaper`).
   - `factory.py`: `ScenarioFactory` para construir adaptadores ViZDoom / Sintéticos sin modificar el núcleo.
4. `env/`:
   - `vizdoom_adapter.py`: `ViZDoomEnvironmentAdapter` desacoplado para cualquier escenario `.cfg`/`.wad` y detector visual opcional para overlays de depuración.
   - `synthetic_arena.py`: `SyntheticArenaAdapter` compatible por LSP para entornos sin binario ViZDoom (combate y recolección).
5. `rl/`:
   - `networks.py`: `ActorCriticCNN` (Nature-CNN sobre `4x84x84`).
   - `rollout_buffer.py`: `RolloutBuffer` con cálculo de ventajas GAE($\gamma, \lambda$).
   - `ppo_agent.py`: `PPOAgent(RLAgent)` con objetivo clipeado PPO, entropía, persistencia y métricas en vivo.
6. `services/simulation_service.py`: `SimulationCoordinator` que inyecta dependencias y coordina SNN + Buffer Visual + PPO + Gemma 3 + control en caliente.
7. `doom_bridge.py` y `motor_policy.py`: Fachadas de compatibilidad hacia atrás para preservar la suite existente de tests.
8. `main.py`: Capa delgada FastAPI + WebSocket + nuevos endpoints `/api/scenario`, `/api/speed`, `/api/episode/reset`.

## Frontend (`frontend/src/`)
- `useTelemetrySocket.js`: Acciones `switchScenario`, `updateSpeed`, `resetEpisode`.
- `LiveArena.jsx` & `TrainingPanel.jsx`: Visualizador en vivo del Buffer Visual (`FrameStack` 4×84×84), selector de escenario en caliente, slider de velocidad (`target_fps` / `tic_skip`), botón de reinicio de episodio, y KPIs de PPO (`FPS`, `loss`, `policy_loss`, `value_loss`, `exploration_rate` / `entropy`).

## Scripts y Documentación
- `scripts/train_ppo.py`: Entrenador CLI multi-escenario en PyTorch puro.
- `.gitignore`, `LICENSE`, `README.md` didáctico y limpio para GitHub.
