# Spec 002 — Refactorización SOLID, PPO Visual Multi-Escenario y Preparación GitHub

Estado: en progreso

## Contexto y objetivo
Refactorizar NeuroDoom OS aplicando estrictamente los principios SOLID (SRP, OCP, LSP, ISP, DIP) para desacoplar ViZDoom, el pipeline del Buffer Visual (`VIZDOOM_NATIVE`), el algoritmo de Aprendizaje por Refuerzo (**PPO en PyTorch puro con CNN + FrameStack**), el conectoma biológico SNN (`connectome_snn.py`), el neuromodulador Gemma 3 y la capa de transporte FastAPI/React.

## Requisitos funcionales (EARS)
- **RF-9 (Pipeline del Buffer Visual):** MIENTRAS el entorno genere frames RGB (`VIZDOOM_NATIVE` o arena sintética), EL SISTEMA preprocesará los píxeles (escala de grises, redimensionamiento a $84 \times 84$, normalización a $[0, 1]$ y apilamiento temporal `FrameStack(k=4)`) produciendo tensores `(4, 84, 84)` puros sin filtrar `labels` hacia la red neuronal, manteniendo además una retina $64 \times 64$ para el conectoma SNN.
- **RF-10 (Fábrica Multi-Escenario Declarativa):** CUANDO se solicite cualquier escenario (`defend_the_center`, `basic`, `deadly_corridor`, `health_gathering`, `defend_the_line` o `.cfg`/`.wad` externos definidos en JSON), EL SISTEMA instanciará mediante `ScenarioFactory` el adaptador correspondiente con sus botones, variables de juego y estrategia de *reward shaping* sin modificar el código fuente central.
- **RF-11 (Agente PPO Modular en PyTorch):** CUANDO el agente opere en modo entrenamiento o evaluación, EL SISTEMA utilizará `PPOAgent` (`ActorCriticCNN` + `RolloutBuffer` con GAE) entrenado sobre el `FrameStack` visual, exponiendo pérdida de política, pérdida de valor, entropía de exploración, FPS reales y persistencia de checkpoints por escenario.
- **RF-12 (Dashboard Interactivo en Tiempo Real):** MIENTRAS el usuario observe el Laboratorio en Vivo en React, EL SISTEMA mostrará el Buffer Visual procesado (mosaico `FrameStack`), la recompensa acumulada, pérdida (`loss`), tasa de exploración/entropía y FPS reales, permitiendo pausar/reanudar, ajustar velocidad (`target_fps` / `tic_skip`), cambiar de escenario en caliente y reiniciar el episodio actual.
- **RF-13 (Repositorio Didáctico para GitHub):** EL SISTEMA incluirá un `.gitignore` estricto (sin `.pt`, `.npz`, `*.png`, logs ni entornos virtuales), `LICENSE` (MIT) y un `README.md` completo con diagramas, explicación SOLID, flujo del Buffer Visual e instrucciones exactas de Git.
