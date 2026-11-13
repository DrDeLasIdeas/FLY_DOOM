# Plan Técnico — Spec 001 NeuroDoom OS

## 1. Mapa de Archivos y Responsabilidades
- `scripts/generate_connectome_graph.py` (RF-1): Crea `data/flywire_subconnectome.npz` con 20,000 neuronas, 600,000 sinapsis dirigidas y coordenadas 3D bilaterales.
- `backend/app/config.py` (RF-2, RF-4): Centraliza constantes biofísicas y variables de entorno.
- `backend/app/connectome_snn.py` (RF-2): Clase `DrosophilaConnectomeEngine` con propagación dispersa `torch.sparse.mm`, integración LIF y trazas R-STDP.
- `backend/app/doom_bridge.py` (RF-3): Clase `DoomFlyEnvironment` con soporte para `vizdoom` nativo y fallback sintético automático (garantiza ejecución en cualquier entorno).
- `backend/app/gemma_neuromodulator.py` (RF-4): Cliente HTTPX asíncrono hacia Ollama con validación de límites y fallback homeostático.
- `backend/app/main.py` (RF-4, RF-5): Servidor FastAPI con loop de fondo para Gemma 3, WebSocket `/ws/telemetry` y endpoints REST `/api/modulate`, `/api/dopamine-pulse` y `/api/health`.
- `tests/test_snn_engine.py` (RF-1, RF-2, RF-3, RF-4): Suite `pytest` que valida generación del grafo, conservación de dimensiones dispersas, disparos LIF, plasticidad dopaminérgica y puente sensorial.
- `frontend/src/*` (RF-6, RF-7): SPA en React 19 + Tailwind CSS con `ConferenceDeck.jsx`, `LiveArena.jsx`, `Connectome3D.jsx`, `SpikeOscilloscope.jsx` y `GemmaBrainConsole.jsx`.
- `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml` (RF-8): Infraestructura ARM64.

## 2. Riesgos y Mitigaciones
- **ViZDoom no disponible en tests:** `DoomFlyEnvironment` conmuta a Cyber-Arena sintética sin interrumpir el bucle.
- **Ollama no responde o tarda:** `gemma_neuromodulator.py` aplica homeostasis local determinista con timeout de 6 s.
- **MPS no soporta operaciones dispersas:** el motor degrada a CPU ARM64 NEON dentro del contenedor Linux.
- **Bloqueo del loop de 35 Hz:** Gemma 3 corre en `asyncio.create_task` y jamás dentro del bucle de telemetría.
