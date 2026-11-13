# Tareas de Implementación — Spec 001 NeuroDoom OS

- [x] **T1. Cimientos, Arnés OpenCode y Generador del Conectoma.** Cubre RF-1.
  Hecho cuando: Existen `AGENTS.md`, `MEMORY.md`, `docs/constitution.md`, `scripts/generate_connectome_graph.py` genera `data/flywire_subconnectome.npz` correctamente.
- [x] **T2. Motor Neuro-Computacional SNN (`config.py` y `connectome_snn.py`).** Cubre RF-2.
  Hecho cuando: `DrosophilaConnectomeEngine` ejecuta pasos biofísicos LIF + R-STDP sobre tensores dispersos y extrae coordenadas 3D muestreadas.
- [x] **T3. Puente ViZDoom con Fallback Sintético y Neuromodulador Gemma 3.** Cubre RF-3, RF-4.
  Hecho cuando: `doom_bridge.py` y `gemma_neuromodulator.py` procesan frames $64 \times 64$, acciones motoras y consultas JSON a Ollama con fallback homeostático.
- [x] **T4. Servidor FastAPI, WebSocket de Telemetría y Suite de Tests (`pytest`).** Cubre RF-2, RF-3, RF-4, RF-5.
  Hecho cuando: `backend/app/main.py` está completo y `pytest tests/ -v` pasa 100% en verde.
- [x] **T5. Estructura Base del Frontend React + Vite + Tailwind y Hook WebSocket.** Cubre RF-5, RF-6, RF-7.
  Hecho cuando: `frontend/package.json`, configuraciones Vite/Tailwind, `useTelemetrySocket.js`, `App.jsx` y `Navbar.jsx` están creados.
- [x] **T6. Componentes Visuales de Conferencia y Laboratorio en Vivo.** Cubre RF-6, RF-7.
  Hecho cuando: `ConferenceDeck.jsx`, `LiveArena.jsx`, `Connectome3D.jsx`, `SpikeOscilloscope.jsx` y `GemmaBrainConsole.jsx` están implementados sin placeholders.
- [x] **T7. Contenerización Docker ARM64 y Scripts de Automatización macOS.** Cubre RF-8.
  Hecho cuando: `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `Makefile` y `scripts/setup_mac.sh` están creados y verificados.
- [x] **T8. Verificación Integral y Cierre.** Cubre RF-1 a RF-8.
  Hecho cuando: El conectoma se regenera, `pytest tests/ -v` pasa en verde, el frontend compila con `npm run build` y `MEMORY.md` queda actualizado.
- [x] **T9. Política Motora Entrenable, Contadores de Combate y Visualización de Bajas.** Cubre RF-5, RF-6, RF-7 (extensión).
  Hecho cuando: `backend/app/motor_policy.py` (72 features, 4 acciones) se entrena por imitación + REINFORCE, `scripts/train_motor_policy.py` genera `data/motor_policy.pt`, `/api/training` controla el entrenamiento en vivo, la UI muestra munición/disparos/bajas/efectividad y curva de aprendizaje, y `pytest` pasa 8/8.

- [x] **T10. Automatización de arranque y entrenamiento.** Cubre RF-8 (extensión).
  Hecho cuando: `scripts/neurodoom.sh` opera `start|stop|restart|status|train|verify|fullscreen|open`, `logs/PIDs` en `.run/`, y el `Makefile` expone `demo/stop/restart/status/train/verify/fullscreen`.

- [x] **T11. Arena fullscreen con gráficas y aceleración del aprendizaje.** Cubre RF-6, RF-7 (extensión).
  Hecho cuando: `FullscreenArena` + gráficas SVG renderizan telemetría, el loop de telemetría (35 Hz) no se bloquea, y el entrenamiento alcanza 100+ bajas nuevas con efectividad >20%.

- [x] **T12. Verificación integral y cierre.** Cubre RF-1 a RF-8.
  Hecho cuando: `pytest` pasa 13/13 en verde, `npm run build` OK, `make verify` OK y el screenshot `neurodoom_fullscreen.png` se genera.

- [x] **T13. Conectoma 3D anatómico con actividad sináptica en vivo.** Cubre RF-6, RF-7 (extensión).
  Hecho cuando: `generate_connectome_graph.py` produce anatomía paramétrica (retina, lóbulos ópticos, cuerpo del hongo, complejo central, MBON, DAN y DNs) sin alterar `pre_idx`/`post_idx`/`weights`; `/api/connectome/topology` sirve posiciones, regiones, sinapsis y mallas convexas; el WebSocket envía `spikes_b64`/`v_b64`; el frontend renderiza con `three` + `@react-three/fiber` en Mission Control y Arena Fullscreen con presets Mosca/Frontal/Explotada; `pytest` pasa 15/15.

