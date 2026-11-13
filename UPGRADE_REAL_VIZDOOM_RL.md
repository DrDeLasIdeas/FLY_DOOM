# PROMPT MAESTRO PARA GEMINI CLI: INTEGRACIÓN DE VIZDOOM REAL Y APRENDIZAJE AUTOMÁTICO DE DEMONIOS

**Rol del Agente:** Principal Reinforcement Learning & Computational Neuroscientist Engineer.  
**Objetivo:** Actualizar el backend y el entorno de `NeuroDoom OS` para reemplazar el renderizador sintético por el **motor gráfico y de juego real de ViZDoom** (con texturas clásicas de Doom), maximizando la automatización del aprendizaje por refuerzo biológico (R-STDP) para que las neuronas descendentes aprendan a disparar y cazar demonios de forma autónoma.

---

## MODIFICACIONES TÉCNICAS REQUERIDAS

### 1. Forzar ViZDoom Nativo con Escenario de Combate Real (`backend/app/doom_bridge.py`)
- Modifica `DoomFlyEnvironment` para que cargue obligatoriamente los binarios y escenarios oficiales de ViZDoom (`defend_the_center.cfg` o `cig.wad` / `doom2.wad` si están disponibles).
- Si faltan los archivos WAD en el contenedor, descarga automáticamente los paquetes estándar de escenarios de ViZDoom en tiempo de ejecución.
- Ajusta el campo de visión (`FOV`), resolución de pantalla (`320x240`) y tasa de refresco para obtener el aspecto visual retro auténtico de DOOM.

### 2. Optimización del Circuito Motor y Disparos Automáticos (`backend/app/doom_bridge.py` y `connectome_snn.py`)
- Refuerza la función de recompensa biofísica (`bio_reward`):
  - **+3.0 de Dopamina (PAM)** por cada demonio abatido (`KILLS` incrementa).
  - **-1.5 de Castigo (PPL1)** por cada punto de daño recibido (`HEALTH` disminuye).
  - **+0.1** por mantener la mira centrada en objetivos rojos (fotorreceptores R7/R8 excitados).
- Ajusta el umbral de disparo de la neurona descendente de ataque (`DNp09`) para que el agente dispare con mayor frecuencia al detectar patrones visuales enemigos en la retina 64x64.

### 3. Mecanismo de Auto-Corrección por Refuerzo (`backend/app/connectome_snn.py`)
- Asegura que la traza de elegibilidad sináptica (`R-STDP`) en la vía `KC -> MBON` reciba pulsos de refuerzo instantáneos cada vez que ocurra un evento de combate (muerte de demonio o daño al jugador), adaptando los pesos sinápticos sin intervención humana.

---

## INSTRUCCIÓN DE EJECUCIÓN PARA GEMINI CLI
Actualiza los archivos existentes en `backend/app/` con estas especificaciones de rendimiento y gráficos reales, asegurando que el servidor FastAPI transmita las imágenes reales de ViZDoom al Dashboard web en tiempo real a 35 FPS.
