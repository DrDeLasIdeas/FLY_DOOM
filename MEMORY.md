# MEMORY.md — NeuroDoom OS

Memoria operativa del proyecto entre sesiones (máximo 50 líneas).

## Estado actual
- **Spec 001 + Spec 002 optimizadas y verificadas**: Arquitectura SOLID desacoplada, agente **PPO-CNN** con actualización asíncrona sin bloquear el WebSocket, `ViZDoomEnvironmentAdapter` con paso terminal inmediato y `KILLCOUNT` nativo, y sintetizador **Web Audio Retro DOOM 100% libre de copyright** con botón `Audio Retro: ON/OFF` en el dashboard.
- `PYTHONPATH=. .venv311/bin/python -m pytest tests/ -v`: **24/24 en verde**.
- `cd frontend && npm run build`: **OK**.
- Latencia SNN (`step_frame`, 4 sub-pasos con `torch.sparse.mm`): **~17 ms** (< 25 ms constitucionales).

## Arquitectura SOLID vigente
- `backend/app/core/interfaces.py`: Contratos `VisualPreprocessor`, `RewardShaper`, `EnvironmentAdapter`, `RLAgent`, `ConnectomeEngine`, `Neuromodulator`.
- `backend/app/connectome_snn.py` + `connectome_serializer.py`: SNN biofísica pura sin alocar tensores por sub-paso; serialización 3D/bitfields delegada a `ConnectomeTelemetrySerializer` (SRP).
- `backend/app/vision/preprocessor.py`: `VisualBufferProcessor` (`4×84×84` + mosaico Base64 + retina `64×64`).
- `backend/app/scenarios/` + `backend/app/env/`: 5 escenarios JSON (`defend_the_center`, `basic`, `defend_the_line`, `deadly_corridor`, `health_gathering`), lectura directa de `KILLCOUNT`/`AMMO2`/`HEALTH` y `episode_finished=True` inmediato en pasos terminales.
- `backend/app/rl/`: `ActorCriticCNN`, `RolloutBuffer` (GAE) y `PPOAgent` con `run_shadow_update` en hilo separado (`asyncio.to_thread`), evitando bloqueos del stream y contaminación en modo `greedy`.
- `backend/app/services/`: `SimulationCoordinator` + `TelemetryPacketBuilder` + `SystemStateStore` + `GemmaNeuromodulatorAdapter` (inicialización diferida en `lifespan` de `main.py`).
- `frontend/src/audio/retroDoomAudio.js` + `hooks/useRetroAudio.js`: Música industrial frigia procedural + SFX reactivos (disparo, baja, daño, curación, dopamina, cambio de escenario) sin archivos externos ni copyright.

## Automatización
- `make demo` / `make train` (`scripts/neurodoom.sh` conectado a `scripts/train_ppo.py` sobre `checkpoints/`).
- Vista `4. Arena Fullscreen` y `?mode=fullscreen` restauradas y sincronizadas con `PPO-CNN`.
