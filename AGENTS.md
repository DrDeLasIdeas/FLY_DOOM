# AGENTS.md — NeuroDoom OS

Plataforma neuro-cibernética que conecta el conectoma biológico de *Drosophila melanogaster* (SNN LIF + R-STDP) con ViZDoom y Gemma 3 (Ollama), equipada con un dashboard interactivo para conferencias en vivo sobre macOS Apple Silicon (ARM64).

## Stack y estructura
- Backend: Python 3.11 + FastAPI + PyTorch (tensores dispersos COO/CSR) + ViZDoom + HTTPX (`backend/app/`).
- Frontend: Node 22 + React 19 + Vite + Tailwind CSS + Lucide React (`frontend/src/`).
- Pruebas y Specs: `tests/` (pytest), `specs/001-neurodoom-os/` (SDD), `data/` (grafo `.npz`).

## Comandos
- Generar conectoma: `python3 scripts/generate_connectome_graph.py`
- Tests Backend: `pytest tests/ -v`
- Levantar Backend local: `uvicorn backend.app.main:app --reload --port 8000`
- Levantar Frontend local: `cd frontend && npm run dev`
- Levantar Stack Docker ARM64: `docker compose up --build`

## Convenciones y Reglas de Dominio
- Nunca densificar la matriz sináptica `self.W`: usar exclusivamente operaciones dispersas (`torch.sparse.mm`).
- El bucle WebSocket de telemetría (35 Hz) jamás debe bloquearse esperando a Ollama (Gemma 3 corre en background task).
- `doom_bridge.py` debe soportar modo fallback sintético si el binario de ViZDoom no está disponible en el entorno de test.

## Reglas SDD y Memoria
- Lee `docs/constitution.md`, `MEMORY.md` y `specs/001-neurodoom-os/` antes de modificar código.
- Al finalizar tareas, actualiza `MEMORY.md` (< 50 líneas) y marca las casillas en `tasks.md`.
