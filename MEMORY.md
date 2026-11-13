# MEMORY.md — NeuroDoom OS

Memoria operativa del proyecto entre sesiones (máximo 50 líneas).

## Estado actual
- **Spec 001 + Spec 002 implementadas**: Refactorización SOLID completa (`core/`, `vision/`, `scenarios/`, `env/`, `rl/`, `services/`), agente **PPO-CNN** en PyTorch puro sobre `FrameStack(4, 84, 84)`, fábrica multi-escenario (`defend_the_center`, `basic`, `defend_the_line`, `deadly_corridor`, `health_gathering`) y dashboard React extendido.
- `PYTHONPATH=. .venv311/bin/python -m pytest tests/ -v`: **21/21 en verde**.
- `cd frontend && npm run build`: **OK**.
- Repo preparado para GitHub: `.gitignore` estricto (sin `.pt`, `.npz`, `*.png`, logs ni venvs), `LICENSE` (MIT) y `README.md` didáctico.

## Arquitectura SOLID
- `backend/app/core/interfaces.py`: Contratos `VisualPreprocessor`, `RewardShaper`, `EnvironmentAdapter`, `RLAgent`, `ConnectomeEngine`, `Neuromodulator`.
- `backend/app/vision/preprocessor.py`: `VisualBufferProcessor` (RGB -> Grayscale -> 84×84 -> `[0,1]` -> `FrameStack(4)` + mosaico Base64 + retina 64×64 para SNN).
- `backend/app/scenarios/`: Configs JSON declarativas + `ScenarioRegistry` + `RewardShaper` strategies + `ScenarioFactory`.
- `backend/app/env/`: `ViZDoomEnvironmentAdapter` + `SyntheticArenaAdapter` (LSP) + `EnemyOverlayDetector` (solo overlay HUD, sin leak a CNN).
- `backend/app/rl/`: `ActorCriticCNN`, `RolloutBuffer` (GAE), `PPOAgent` con hot-swap multi-escenario y checkpoints en `checkpoints/`.
- `backend/app/services/simulation_service.py`: `SimulationCoordinator` desacoplado de FastAPI (`main.py` delgado).

## Endpoints y controles en vivo
- `GET /api/scenarios`, `POST /api/scenario` (cambio en caliente), `POST /api/speed` (`target_fps` / `tic_skip`), `POST /api/episode/reset`.
- `doom_bridge.py` y `motor_policy.py` conservados como fachadas compatibles con los tests heredados.
- `backend/Dockerfile` copia `backend/app /app/app`; mantener imports relativos dentro de `backend/app/`.

## Próximos pasos
- Entrenar checkpoints PPO por escenario con `scripts/train_ppo.py --scenario <id> --episodes 50` o inicializar y subir a GitHub con los comandos del `README.md`.
