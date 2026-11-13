# DOCUMENTO MAESTRO DE ARQUITECTURA E IMPLEMENTACIÓN: NEURODOOM OS (V2 ENHANCED)
**Proyecto:** NeuroDoom OS — Conectoma Biológico de *Drosophila melanogaster* Jugando DOOM + Plataforma Interactiva de Conferencia
**Arquitectura Objetivo:** macOS Apple Silicon (ARM64 / Serie M) — 100% Local (Docker ARM64 + Aceleración GPU Metal MPS + Ollama Gemma 3 Local)

## 0. INSTRUCCIONES ESTRICTAS PARA EL AGENTE (GEMINI CLI)
Actúa como Principal Systems Architect, Computational Neuroscientist y Senior Full-Stack Engineer.
1. Genera TODOS los archivos del proyecto dentro del directorio actual (`FLY_DOOM/`) siguiendo exactamente la estructura y el código especificados en este documento.
2. PROHIBIDO dejar bloques `TODO`, `pass`, placeholders o código incompleto.
3. PROHIBIDO usar APIs de IA en la nube dentro del código generado. El Sistema 2 (Neuromodulador) se conecta exclusivamente a Ollama en local (`http://host.docker.internal:11434` en Docker o `http://localhost:11434` en nativo).
4. Respeta estrictamente el contrato JSON del WebSocket `/ws/telemetry` tanto en `backend/app/main.py` como en todos los componentes de `frontend/src/`.

---

## 1. ESTRUCTURA EXACTA DE ARCHIVOS A GENERAR EN EL DIRECTORIO ACTUAL
```text
./
├── GEMINI.md
├── docker-compose.yml
├── Makefile
├── README.md
├── scripts/
│   ├── setup_mac.sh
│   └── generate_connectome_graph.py
├── data/
│   └── flywire_subconnectome.npz
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── config.py
│       ├── connectome_snn.py
│       ├── doom_bridge.py
│       ├── gemma_neuromodulator.py
│       └── main.py
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── index.css
        ├── App.jsx
        ├── hooks/
        │   └── useTelemetrySocket.js
        └── components/
            ├── Navbar.jsx
            ├── ConferenceDeck.jsx
            ├── LiveArena.jsx
            ├── Connectome3D.jsx
            ├── SpikeOscilloscope.jsx
            └── GemmaBrainConsole.jsx