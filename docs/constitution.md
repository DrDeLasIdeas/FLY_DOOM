# Constitución — NeuroDoom OS

Principios innegociables del sistema. Toda spec, plan, tarea y línea de código debe cumplirlos:

1. **Simplicidad y Compatibilidad ARM64**: Mantener el stack definido en `AGENTS.md`. Todo contenedor y dependencia debe compilar y correr nativamente en `linux/arm64` (Apple Silicon) sin emulación Rosetta.
2. **La Spec manda**: Todo desarrollo sigue `specs/001-neurodoom-os/spec.md`. Prohibido dejar bloques `TODO` o funciones sin implementar.
3. **Biofísica Pura y Desacoplada**: El motor `connectome_snn.py` debe funcionar como un módulo matemático puro sin depender de FastAPI ni de ViZDoom, permitiendo su validación directa con `pytest`.
4. **Tests y Resiliencia en Escenario (TDD)**: El sistema nunca puede colapsar durante la conferencia. Si Ollama o ViZDoom fallan o tardan en responder, el sistema activa fallbacks homeostáticos y sintéticos transparentes.
5. **Tiempo Real No Bloqueante**: La integración neuronal LIF + R-STDP debe mantener latencias menores a 25 ms por ciclo; las llamadas a LLMs locales (Gemma 3) son estrictamente asíncronas.
6. **Idioma**: Código fuente, variables y endpoints en inglés; interfaz gráfica de la conferencia, explicaciones científicas y documentación SDD en español.
