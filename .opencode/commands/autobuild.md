---
description: Construye y verifica automáticamente todo el proyecto NeuroDoom OS siguiendo la spec 001
agent: build
---
Ejecuta en modo 100% autónomo todas las tareas pendientes de `specs/001-neurodoom-os/tasks.md` siguiendo `specs/001-neurodoom-os/plan.md`, `docs/constitution.md` y `@NEURODOOM_OPENCODE_MASTER.md`.
1. Genera todos los archivos de configuración, scripts, backend, tests, frontend y Docker.
2. Ejecuta `python3 scripts/generate_connectome_graph.py` y `pytest tests/ -v`.
3. Marca todas las tareas completadas con `[x]` en `specs/001-neurodoom-os/tasks.md` y actualiza `MEMORY.md`.
