# Tareas — Spec 002 Refactorización SOLID + PPO Visual + Audio Retro

- [x] **T14. Contratos SOLID (`core/interfaces.py`) y Pipeline Visual (`vision/preprocessor.py`).** Cubre RF-9.
- [x] **T15. Fábrica Multi-Escenario (`scenarios/`) y Adaptadores (`env/vizdoom_adapter.py`, `env/synthetic_arena.py`, `doom_bridge.py`) con pasos terminales inmediatos y `KILLCOUNT`.** Cubre RF-10.
- [x] **T16. Agente PPO Modular en PyTorch (`rl/networks.py`, `rl/rollout_buffer.py`, `rl/ppo_agent.py`) con shadow update asíncrono y `scripts/train_ppo.py`.** Cubre RF-11.
- [x] **T17. Orquestador SOLID (`services/simulation_service.py`, `telemetry_builder.py`, `state_store.py`, `connectome_serializer.py`, `GemmaNeuromodulatorAdapter`), API FastAPI (`main.py`), Audio Retro WebAudio sin copyright (`retroDoomAudio.js`) y Dashboard React extendido.** Cubre RF-12.
- [x] **T18. Tests (`tests/`), `.gitignore` estricto, `LICENSE`, `README.md` didáctico y verificación integral.** Cubre RF-9 a RF-13.
