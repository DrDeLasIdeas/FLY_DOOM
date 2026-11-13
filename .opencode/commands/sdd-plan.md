---
description: Crea o actualiza el plan técnico de la spec 001
agent: planner
---
Actualiza `specs/001-neurodoom-os/plan.md` mapeando cada requisito funcional de `spec.md` a archivos y responsabilidades concretas.

Reglas:
- Mantén la arquitectura ARM64 descrita en `docs/constitution.md`.
- No propongas dependencias incompatibles con `linux/arm64`.
- Añade riesgos y mitigaciones (fallback de ViZDoom, fallback homeostático de Ollama).

Argumentos del usuario: $ARGUMENTS
