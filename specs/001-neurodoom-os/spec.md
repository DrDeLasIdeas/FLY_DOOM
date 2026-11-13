# Spec 001 — Sistema Integral NeuroDoom OS (Conectoma SNN + ViZDoom + Gemma 3 + UI Conferencia)
Estado: aprobada

## Contexto y objetivo
Construir una plataforma neuro-cibernética reproducible en macOS Apple Silicon (ARM64) donde el conectoma modelado de *Drosophila melanogaster* (20,000 neuronas y 600,000 sinapsis escalables a la topología FlyWire v783) juegue DOOM en tiempo real mediante dinámicas Leaky Integrate-and-Fire (LIF) y plasticidad modulada por dopamina (R-STDP), asistido por Gemma 3 en Ollama como Sistema 2 neuromodulador, y visualizado en una interfaz web interactiva para conferencias.

## Usuarios / Actores
- **Ponente / Investigador:** Controla la presentación interactiva de 5 etapas, inyecta pulsos de dopamina y ajusta umbrales biofísicos en vivo frente al público.
- **Audiencia de la Conferencia:** Visualiza en tiempo real la retina de la mosca, el conectoma 3D, el osciloscopio de espigas y las decisiones neuroquímicas de Gemma 3.

## Requisitos funcionales (criterios de aceptación en EARS)
- **RF-1 (Generación del Conectoma):** CUANDO se ejecute `scripts/generate_connectome_graph.py`, EL SISTEMA generará el archivo comprimido `data/flywire_subconnectome.npz` con tensores dispersos (`pre_idx`, `post_idx`, `weights`) y coordenadas 3D anatómicas (`coords_3d`) de las 7 poblaciones de *Drosophila*.
- **RF-2 (Simulación Biofísica LIF + R-STDP):** MIENTRAS el motor `DrosophilaConnectomeEngine` esté activo, EL SISTEMA integrará el voltaje de membrana $V_i(t)$, la corriente sináptica dispersa $I_{syn, i}(t)$ y la plasticidad modulada por dopamina a $k=4$ sub-pasos por frame sin superar $25\text{ ms}$ de latencia.
- **RF-3 (Puente Sensorial-Motor y Fallback):** CUANDO el motor decodifique las tasas de disparo de las Neuronas Descendentes (`dn_left`, `dn_right`, `dn_attack`), EL SISTEMA ejecutará la acción correspondiente en ViZDoom (o en el simulador sintético de respaldo si ViZDoom no está instalado) y devolverá el frame RGB, la matriz retinotópica $64 \times 64$ y la señal de recompensa biológica.
- **RF-4 (Neuromodulación Asíncrona con Gemma 3):** CADA 5 segundos de operación continua, EL SISTEMA consultará asíncronamente a Ollama (`gemma3:4b`) con la telemetría reciente y ajustará `v_thresh`, `dopamine_lr`, `sensory_gain` y `noise_std` dentro de rangos biofísicos seguros, o aplicará regulación homeostática local si Ollama no responde.
- **RF-5 (Streaming WebSocket e Intervención Manual):** MIENTRAS un cliente web esté conectado a `/ws/telemetry`, EL SISTEMA transmitirá paquetes JSON a $\sim 30\text{--}35\text{ Hz}$ con frames en Base64, tasas de disparo, actividad 3D muestreada y estado de Gemma 3, y aceptará comandos en `/api/modulate` y `/api/dopamine-pulse`.
- **RF-6 (Modo Conferencia Interactiva de 5 Etapas):** CUANDO el usuario seleccione "Modo Conferencia" en el Frontend, EL SISTEMA mostrará un stepper interactivo de 5 etapas con las fórmulas matemáticas, comparativa visual de omatidios y simulador interactivo de neurona LIF en vivo.
- **RF-7 (Laboratorio de Telemetría en Vivo):** CUANDO el usuario seleccione "Laboratorio en Vivo", EL SISTEMA mostrará simultáneamente el stream de ViZDoom, la retina $64 \times 64$, el visor 3D rotatorio en Canvas del conectoma, el osciloscopio multicapa y la consola de Gemma 3 con botones de inyección de dopamina (`+PAM` / `-PPL1`).
- **RF-8 (Contenerización Nativa ARM64):** CUANDO se ejecute `docker compose up --build`, EL SISTEMA compilará y levantará `neurodoom-core` (puerto 8000) y `neurodoom-ui` (puerto 3000) sobre `linux/arm64`.
