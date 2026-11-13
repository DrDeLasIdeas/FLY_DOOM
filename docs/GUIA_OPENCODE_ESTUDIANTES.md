# Guía para Estudiantes y Desarrolladores: Cómo Ejecutar NeuroDoom OS (`FLY_DOOM`) con OpenCode

Esta guía explica paso a paso cómo cualquier estudiante o desarrollador puede **clonar este repositorio, instalar dependencias, entrenar el agente RL (PPO-CNN) en ViZDoom y levantar el dashboard en vivo** utilizando **OpenCode** desde su computadora (macOS Apple Silicon, Linux o Windows con WSL2).

---

## 1. ¿Qué incluye este repositorio para OpenCode?

El proyecto ya viene preconfigurado con un entorno **Spec-Driven Development (SDD)** listo para OpenCode:
* `AGENTS.md`: reglas de arquitectura, comandos y convenciones del proyecto que OpenCode lee automáticamente al iniciar.
* `opencode.json`: configuración de *skills* locales (`.agents/skills/`) y herramientas MCP.
* `.opencode/agents/`: subagentes especializados (`coordinator`, `planner`, `implementer`, `reviewer`).
* `.opencode/commands/`: comandos rápidos (`/sdd-spec`, `/sdd-plan`, `/sdd-tasks`, `/sdd-implement`, `/sdd-validate`, `/autobuild`).
* `docs/constitution.md` y `specs/`: principios técnicos y especificaciones del proyecto.

---

## 2. Requisitos previos en tu computadora

Antes de abrir OpenCode, asegúrate de tener instalado:

1. **Git**
2. **Python 3.11** (recomendado por compatibilidad con `torch==2.4.1` y `vizdoom==1.2.4`)
3. **Node.js 20 o 22+** y `npm`
4. **OpenCode** instalado en tu terminal (`opencode --version`)
   * Si aún no lo tienes: consulta la guía oficial en [opencode.ai](https://opencode.ai) o instálalo vía `npm i -g opencode-ai` / `brew install anomalyco/tap/opencode`.
5. *(Opcional)* **Ollama** con `gemma3:4b` (`ollama pull gemma3:4b`) para la neuromodulación LLM en vivo. Si no lo tienes instalado, el sistema activa automáticamente el **modo homeostático de respaldo** sin fallar.

---

## 3. Clonar el proyecto e iniciar OpenCode

Abre tu terminal y ejecuta:

```bash
git clone https://github.com/DrDeLasIdeas/FLY_DOOM.git
cd FLY_DOOM
opencode
```

> **Tip:** Al abrir `opencode` dentro de `FLY_DOOM`, te pedirá elegir o tener configurado un proveedor/modelo (por ejemplo Anthropic, OpenAI, Google Gemini o un modelo local en Ollama). Una vez dentro del chat de OpenCode, ya puedes darle instrucciones en lenguaje natural.

---

## 4. Prompts listos para copiar y pegar en OpenCode

No necesitas memorizar comandos complejos. Copia y pega cualquiera de estos prompts dentro de **OpenCode**:

### A) Instalación automática y verificación inicial (primer uso)
```text
Lee README.md y AGENTS.md. Crea un entorno virtual con Python 3.11 en .venv311, instala backend/requirements.txt, instala las dependencias de frontend/ con npm install, genera el conectoma con scripts/generate_connectome_graph.py y ejecuta la suite de tests pytest tests/ -v para verificar que todo funciona en mi máquina.
```

### B) Levantar la plataforma y el Dashboard en vivo
```text
Levanta el backend FastAPI en el puerto 8000 y el frontend Vite en el puerto 3000 usando .venv311. Verifica que http://127.0.0.1:8000/api/health responda ok y dime la URL para abrir el dashboard en mi navegador.
```
Luego abre en tu navegador **`http://127.0.0.1:3000`** y entra a la pestaña **2. Laboratorio en Vivo (Mission Control)** para ver:
* Stream de ViZDoom en tiempo real (`VIZDOOM_NATIVE` o `SYNTHETIC_ARENA`)
* **Buffer CNN (`4×84×84`)** procesado en vivo (escala de grises, normalizado y apilado)
* **Retina SNN (`64×64`)** y Conectoma 3D interactivo
* Selector de escenarios en caliente, control de FPS/`tic_skip`, reinicio de episodio y gráficas de recompensa, *loss* y exploración.

### C) Entrenar al agente PPO-CNN en diferentes escenarios
```text
Entrena el agente PPO-CNN con scripts/train_ppo.py durante 25 episodios en el escenario basic y luego 25 episodios en defend_the_center. Muéstrame la evolución de recompensa, pérdida (loss), tasa de exploración y FPS.
```
Escenarios disponibles de fábrica:
* `defend_the_center`
* `basic`
* `defend_the_line`
* `deadly_corridor`
* `health_gathering`

### D) Agregar un nuevo escenario personalizado (`.cfg` / `.wad`) sin tocar el núcleo
```text
Quiero agregar un escenario personalizado de ViZDoom llamado "mi_arena" usando el flujo SOLID del proyecto (sin modificar código fuente principal). Crea el archivo declarativo en backend/app/scenarios/configs/mi_arena.json y agrega un test en tests/ que valide que ScenarioFactory lo carga correctamente.
```

### E) Explorar y entender el código (modo estudio)
```text
Explícame paso a paso cómo fluye un frame desde ViZDoom hasta la decisión de acción en backend/app/: qué hace VisualBufferProcessor, cómo calcula las ventajas RolloutBuffer, cómo actualiza pesos PPOAgent y dónde se aplican los 5 principios SOLID.
```

---

## 5. Uso de comandos SDD integrados en OpenCode

Dentro del chat de OpenCode puedes invocar directamente los comandos definidos en `.opencode/commands/`:

* `/sdd-spec <tu idea>` — Redacta una nueva especificación funcional en `specs/`.
* `/sdd-plan` — Genera el plan técnico respetando `docs/constitution.md`.
* `/sdd-tasks` — Desglosa el plan en tareas verificables.
* `/sdd-implement` — Implementa la siguiente tarea pendiente y corre `pytest`.
* `/sdd-validate` — Audita calidad y cumplimiento de requisitos.

---

## 6. Referencia rápida manual (si prefieres ejecutar en terminal sin OpenCode)

```bash
# 1. Crear entorno Python 3.11 e instalar backend
python3.11 -m venv .venv311
source .venv311/bin/activate          # En Windows PowerShell: .venv311\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r backend/requirements.txt

# 2. Generar grafo del conectoma (data/flywire_subconnectome.npz)
PYTHONPATH=. python scripts/generate_connectome_graph.py

# 3. Instalar frontend
cd frontend && npm install && cd ..

# 4. Ejecutar pruebas automatizadas
PYTHONPATH=. pytest tests/ -v

# 5. Entrenar PPO en un escenario
PYTHONPATH=. python scripts/train_ppo.py --scenario defend_the_center --episodes 30

# 6. Iniciar servicios en dos terminales
# Terminal 1:
PYTHONPATH=. .venv311/bin/uvicorn backend.app.main:app --reload --port 8000
# Terminal 2:
cd frontend && npm run dev -- --port 3000
```

En macOS también puedes usar los atajos del `Makefile`:
```bash
make demo      # Arranca backend + frontend
make status    # Verifica estado y métricas
make stop      # Detiene servicios guardando el aprendizaje
```

---

## 7. Solución de problemas frecuentes

* **`ModuleNotFoundError: No module named 'backend'` al correr `pytest` o scripts**:
  Ejecuta siempre desde la raíz del proyecto anteponiendo `PYTHONPATH=.` (por ejemplo: `PYTHONPATH=. pytest tests/ -v`).
* **ViZDoom no compila o no abre ventana en tu sistema**:
  No bloquea el proyecto. El sistema cambia automáticamente a `SYNTHETIC_ARENA` (`SyntheticArenaAdapter`) cumpliendo la misma interfaz `EnvironmentAdapter` para que puedas estudiar, probar y entrenar el pipeline completo. Puedes forzarlo con `--force-synthetic` en `scripts/train_ppo.py`.
* **Ollama (`gemma3:4b`) no está instalado**:
  El backend detecta automáticamente la ausencia de Ollama y activa el **fallback homeostático** sin interrumpir el streaming WebSocket.
* **Puertos `8000` o `3000` ocupados**:
  En macOS/Linux puedes liberar procesos previos con `./scripts/neurodoom.sh stop` o cambiar el puerto con `--port`.
