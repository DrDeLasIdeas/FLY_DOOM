# NEURODOOM_OPENCODE_MASTER.md

Documento maestro de ejecución para NeuroDoom OS. La fuente de verdad operativa son
`docs/constitution.md` y `specs/001-neurodoom-os/` (`spec.md`, `plan.md`, `tasks.md`).

## Objetivo
Plataforma neuro-cibernética local en macOS Apple Silicon (ARM64) donde el conectoma
modelado de *Drosophila melanogaster* (SNN LIF + R-STDP) juega DOOM en ViZDoom y es
neuromodulado por Gemma 3 vía Ollama, con dashboard interactivo para conferencias.

## Arquitectura
- **Host macOS:** Ollama nativo sirviendo `gemma3:4b` en `localhost:11434` (Metal).
- **Docker `linux/arm64`:**
  - `neurodoom-core` (8000): ViZDoom headless + PyTorch disperso + FastAPI/WebSocket.
  - `neurodoom-ui` (3000): React 19 + Vite + Tailwind.
- **Puente host:** `http://host.docker.internal:11434`.

## Matemática del conectoma (FlyWire v783)
- Matriz sináptica dispersa COO/CSR: `W_ij = n_syn(j→i) · s_j · g_scale`.
- LIF: `τ_m dV_i/dt = (V_rest - V_i) + I_syn,i + I_ext,i + η_i`.
- R-STDP: `dW_plastic/dt = η_da · (r_PAM - r_PPL1) · E_ij(t)`.
- Parámetros: `V_rest=-52 mV`, `V_reset=-52 mV`, `V_th=-45 mV`, `τ_m=20 ms`, `τ_syn=5 ms`.

## Fases de construcción
1. Arnés OpenCode: `AGENTS.md`, `MEMORY.md`, `opencode.json`, `docs/constitution.md`,
   `.agents/skills/`, `.opencode/commands/`, `.opencode/agents/`.
2. SDD: `specs/001-neurodoom-os/{spec,plan,tasks}.md`.
3. Backend y datos: `scripts/generate_connectome_graph.py`, `backend/app/*`,
   `backend/requirements.txt`, `backend/Dockerfile`.
4. TDD: `tests/test_snn_engine.py` + `pytest tests/ -v`.
5. Frontend: `frontend/` completo (React 19 + Vite + Tailwind + Lucide).
6. Orquestación: `docker-compose.yml`, `Makefile`, `scripts/setup_mac.sh`.

## Comandos de verificación
```bash
python3 scripts/generate_connectome_graph.py
PYTHONPATH=. pytest tests/ -v
cd frontend && npm install && npm run build
docker compose config
docker compose up --build
```

## Reglas no negociables
- Nunca densificar `self.W`; usar `torch.sparse.mm`.
- El WebSocket de 35 Hz nunca espera a Ollama; Gemma 3 corre en background task.
- ViZDoom y Ollama tienen fallback sintético/homeostático transparente.
- Código y endpoints en inglés; UI, ciencia y SDD en español.
