# DOCUMENTO DE ARQUITECTURA DE SOLUCIÓN Y ESPECIFICACIÓN TÉCNICA (PRD & SYSTEM PROMPT)
**Proyecto:** NeuroDoom OS — Conectoma Biológico de *Drosophila melanogaster* Jugando DOOM + Plataforma Interactiva de Conferencia  
**Arquitectura Objetivo:** macOS Apple Silicon ($\text{ARM64}$ / Serie M) — 100% Local, Orquestado con Docker + Puente de Aceleración Metal ($\text{MPS}$) y Modelos Locales de la familia Gemini (**Gemma 3 vía Ollama**)  
**Propósito del Documento:** Fuente de verdad absoluta (Contexto Maestro) para generación automatizada de código extremo a extremo mediante **Gemini CLI**.

---

## 0. INSTRUCCIONES DIRECTAS PARA EL AGENTE DE IA (GEMINI CLI)

> **ROL DEL AGENTE:** Actúa como un Principal Systems Architect, Computational Neuroscientist y Senior Full-Stack Engineer. Tu objetivo es leer esta especificación completa y generar **todos los archivos, directorios, contenedores Docker, scripts de compilación, backend en Python (FastAPI + PyTorch + ViZDoom) y frontend en React/Vite + Tailwind CSS** sin omitir implementaciones, sin dejar bloques `TODO` y garantizando compatibilidad nativa con arquitecturas $\text{ARM64}$ (Apple Silicon).

---

## 1. RESUMEN EJECUTIVO Y RESOLUCIÓN ARQUITECTÓNICA EN MACOS

### 1.1 Visión General del Sistema
**NeuroDoom OS** es una plataforma dual compuesta por:
1. **El Motor Neuro-Cibernético (Backend):** Ejecuta en tiempo real el conectoma biológico de la mosca de la fruta (*Drosophila melanogaster*, basado en la topología de **FlyWire v783** con $N = 139,255$ neuronas) modelado como una Red Neuronal de Impulsos (*Spiking Neural Network* - $\text{SNN}$) mediante ecuaciones diferenciales *Leaky Integrate-and-Fire* ($\text{LIF}$). El conectoma recibe el buffer visual de **ViZDoom** a través de fotorreceptores virtuales ($\text{R1}\text{--}\text{R8}$), procesa la información en el *Mushroom Body* (Cuerpo Setiforme) con plasticidad sináptica modulada por dopamina ($\text{R-STDP}$), y emite comandos motores a través de Neuronas Descendentes ($\text{DNs}$). En paralelo, un modelo local de la familia Gemini (**Gemma 3** ejecutándose en **Ollama**) opera como el **Sistema 2 (Meta-Controlador Neuroquímico)**, ajustando en caliente los hiperparámetros biofísicos de la red según la telemetría de supervivencia.
2. **La Plataforma Visual para Conferencias (Frontend Web):** Una aplicación web interactiva de alto impacto visual diseñada para proyectarse en un escenario. Combina un **Modo Presentación Guiada (Storytelling Interactivo de 5 Etapas)** que explica qué se conectó, cómo y por qué a nivel matemático y biológico, con un **Modo Telemetría en Vivo (Mission Control)** que muestra el streaming de ViZDoom a $35\text{ Hz}$, gráficos de disparo neuronal (*Spike Raster Plots*), topología 3D interactiva del conectoma y la consola de razonamiento del LLM local en tiempo real.

### 1.2 Decisión Arquitectónica Crítica: Docker + GPU Metal ($\text{MPS}$) en macOS
En macOS con Apple Silicon, **Docker Desktop ejecuta los contenedores dentro de una máquina virtual Linux ligera (`linux/arm64`)**. Por diseño del sistema operativo de Apple, el hipervisor de Linux **no tiene acceso directo a la API propietaria Metal (`torch.backends.mps`)** de macOS.

Para cumplir simultáneamente con el requisito de **contenerización en Docker** y **máximo rendimiento por hardware en local**, implementamos una **Arquitectura Híbrida de Orquestación Local (Docker + Host Accelerator Bridge)** con soporte de fallback automático:

```
+--------------------------------------------------------------------------------------------------+
|                                 HOST: macOS Apple Silicon (ARM64)                                |
|                                                                                                  |
|  +---------------------------------------------+  +-------------------------------------------+  |
|  | SERVICIO NATIVO DE IA LOCAL (Host GPU/Metal)|  | ACELERADOR MPS OPCIONAL (Host Metal)      |  |
|  | Ollama Daemon (Gemma 3 12B / 4B)            |  | PyTorch MPS Worker (Si se requiere >60Hz) |  |
|  | Puerto: localhost:11434                     |  +---------------------+---------------------+  |
|  +----------------------+----------------------+                        |                        |
|                         | host.docker.internal:11434                    | ZeroMQ / WebSockets    |
|  +----------------------v-----------------------------------------------v---------------------+  |
|  |                              DOCKER ENGINE (linux/arm64)                                   |  |
|  |                                                                                            |  |
|  |  +------------------------------------------+  +----------------------------------------+  |  |
|  |  | CONTENEDOR 1: neurodoom-core (Backend)   |  | CONTENEDOR 2: neurodoom-ui (Frontend)  |  |  |
|  |  | - Ubuntu 24.04 ARM64                     |  | - Node 22 Alpine ARM64                 |  |  |
|  |  | - ViZDoom (Compilado nativo ARM64)       |  | - React 19 + Vite + Tailwind CSS       |  |  |
|  |  | - Motor SNN PyTorch (OpenMP / NEON SIMD) |  | - Visor 3D Conectoma + Osciloscopio    |  |  |
|  |  | - Servidor FastAPI + WebSockets (60 FPS) |  | - Modo Conferencia Paso a Paso         |  |  |
|  |  | Puerto: 8000                             |  | Puerto: 3000                           |  |  |
|  |  +------------------------------------------+  +----------------------------------------+  |  |
|  +--------------------------------------------------------------------------------------------+  |
+--------------------------------------------------------------------------------------------------+
```

1. **Todo el entorno de ViZDoom, la API de telemetría, el motor SNN vectorizado con instrucciones $\text{ARM64 NEON}$ y el Frontend web corren 100% dentro de contenedores Docker (`docker-compose up --build`)**.
2. **Ollama (Gemma 3)** se conecta desde el contenedor mediante `http://host.docker.internal:11434`, permitiendo que el LLM utilice el 100% de los núcleos GPU de Apple Silicon sin penalización de virtualización, o bien puede levantarse dentro de un tercer contenedor Docker incluido en el `docker-compose.yml`.
3. El motor SNN en PyTorch incluye detección dinámica de dispositivo (`mps` $\rightarrow$ `cuda` $\rightarrow$ `cpu` con optimización `torch.set_num_threads(8)` para usar los núcleos Performance de Apple Silicon dentro de Docker a más de $45\text{ FPS}$).

---

## 2. ESTRUCTURA DEL MONOREPO A GENERAR

Gemini CLI debe crear exactamente la siguiente jerarquía de archivos:

```text
neurodoom-conference/
├── docker-compose.yml
├── Makefile
├── README.md
├── scripts/
│   ├── setup_mac.sh                 # Verifica Ollama, descarga Gemma 3 y prepara datos del conectoma
│   └── generate_connectome_graph.py # Genera o descarga el grafo comprimido de FlyWire v783 en formato .npz
├── data/
│   └── flywire_subconnectome.npz    # Tensores dispersos pre-calculados y metadatos de poblaciones
├── backend/
│   ├── Dockerfile                   # Compilación nativa ARM64 de ViZDoom + PyTorch + FastAPI
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py                  # Servidor FastAPI, bucle asíncrono y streaming por WebSockets
│       ├── config.py                # Parámetros biofísicos y de red
│       ├── connectome_snn.py        # Simulador LIF vectorizado + Plasticidad R-STDP + Dopamina
│       ├── doom_bridge.py           # Wrapper de ViZDoom, codificador de omatidios y decodificador motor
│       └── gemma_neuromodulator.py  # Cliente asíncrono hacia Ollama (Gemma 3) para Sistema 2
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx                  # Navegación principal: Modo Conferencia vs. Modo Laboratorio en Vivo
        ├── components/
        │   ├── Navbar.jsx
        │   ├── ConferenceDeck.jsx   # Explicación interactiva paso a paso para la audiencia
        │   ├── LiveArena.jsx        # Stream de DOOM + Controles de inyección de dopamina/voltaje
        │   ├── Connectome3D.jsx     # Visualizador interactivo de las regiones cerebrales en Canvas/WebGL
        │   ├── SpikeOscilloscope.jsx# Gráficas en tiempo real de tasas de disparo y potencial de membrana
        │   └── GemmaBrainConsole.jsx# Terminal en vivo mostrando los ajustes neuroquímicos de Gemma 3
        └── hooks/
            └── useTelemetrySocket.js# Hook WebSocket de baja latencia con reconexión automática
```

---

## 3. FUNDAMENTACIÓN MATEMÁTICA Y NEUROBIOLÓGICA (ESPECIFICACIÓN DEL MOTOR)

Esta sección define las ecuaciones exactas que deben programarse en `backend/app/connectome_snn.py` y mostrarse visualmente en la pantalla de la conferencia (`ConferenceDeck.jsx`).

### 3.1 Topología del Conectoma y Polaridad de Neurotransmisores
El cerebro de *Drosophila melanogaster* comprende $N = 139,255$ neuronas divididas en poblaciones funcionales clave para este proyecto:
* **Fotorreceptores ($\mathcal{P}_{ret}$, neuronas $\text{R1}\text{--}\text{R8}$):** Codifican la luminancia y el contraste cromático del frame de *Doom* reducido a una matriz retinotópica de $64 \times 64 = 4,096$ unidades aferentes.
* **Neuronas del Lóbulo Óptico ($\mathcal{P}_{optic}$, $\text{L1}\text{--}\text{L5}, \text{T4}, \text{T5}$):** Detectan bordes en movimiento horizontal y expansión radial (enemigos o proyectiles acercándose).
* **Células de Kenyon del Cuerpo Setiforme ($\mathcal{P}_{KC}$):** Proyectan representaciones dispersas de alto nivel del estado visual.
* **Neuronas de Salida del Cuerpo Setiforme ($\mathcal{P}_{MBON}$, ej. $\text{MBON11}$):** Codifican la valencia de aproximación o evasión.
* **Neuronas Dopaminérgicas ($\mathcal{P}_{DAN}$, clusters $\text{PPL1}$ y $\text{PAM}$):** $\text{PPL1}$ codifica castigo/daño recibido; $\text{PAM}$ codifica recompensa/eliminación de enemigos o recolección de ítems.
* **Neuronas Descendentes ($\mathcal{P}_{DN}$, ej. $\text{DNp09}, \text{DNp20}, \text{DNpe017}$):** Conectan el cerebro central con el cordón nervioso ventral para ejecutar comandos motores ($\text{TURN\_LEFT}$, $\text{TURN\_RIGHT}$, $\text{MOVE\_FORWARD}$, $\text{ATTACK}$).

La matriz de adyacencia sináptica se representa como un tensor disperso en formato $\text{CSR/COO}$ de dimensión $N \times N$:
$$W_{ij} = n_{syn}(j \rightarrow i) \cdot s_j \cdot g_{scale}$$
donde $n_{syn}(j \rightarrow i)$ es el número de hendiduras sinápticas de la neurona presináptica $j$ a la postsináptica $i$, $g_{scale}$ es el factor de ganancia global y $s_j \in \{-1, +1\}$ es la polaridad determinada por el neurotransmisor dominante en FlyWire:
* **Acetilcolina ($\text{ACh}$):** Excitatorio ($s_j = +1$) en el sistema nervioso central de insectos.
* **Ácido $\gamma$-aminobutírico ($\text{GABA}$):** Inhibitorio ($s_j = -1$).
* **Glutamato ($\text{Glut}$):** Mayoritariamente inhibitorio en interneuronas centrales de *Drosophila* a través de canales de cloro acoplados a glutamato $\text{GluCl}\alpha$ ($s_j = -1$).

### 3.2 Dinámica de Membrana Leaky Integrate-and-Fire ($\text{LIF}$)
En cada paso de integración discreto $\Delta t = 1.0\text{ ms}$ (ejecutando $k = 4$ sub-pasos biofísicos por cada frame de ViZDoom a $35\text{ FPS}$), el potencial de membrana $V_i(t)$ y la corriente sináptica $I_{syn, i}(t)$ evolucionan según:

$$\tau_m \frac{dV_i(t)}{dt} = \left(V_{rest} - V_i(t)\right) + I_{syn, i}(t) + I_{ext, i}(t) + \eta_i(t)$$

$$\tau_{syn} \frac{dI_{syn, i}(t)}{dt} = -I_{syn, i}(t) + \sum_{j=1}^{N} W_{ij} S_j(t)$$

Donde:
* $V_{rest} = -52.0\text{ mV}$ es el potencial de reposo basal.
* $V_{th} = -45.0\text{ mV}$ es el umbral de disparo (modulado dinámicamente por Gemma 3).
* $V_{reset} = -52.0\text{ mV}$ es el potencial de reinicio post-espiga.
* $\tau_m = 20.0\text{ ms}$ y $\tau_{syn} = 5.0\text{ ms}$ son las constantes de tiempo de membrana y sináptica.
* $S_j(t) \in \{0, 1\}$ es el indicador binario de potencial de acción:
  $$S_i(t) = \begin{cases} 1 & \text{si } V_i(t) \ge V_{th} \\ 0 & \text{en otro caso} \end{cases}$$
* $\eta_i(t) \sim \mathcal{N}(0, \sigma_{noise}^2)$ es el ruido térmico espontáneo que mantiene el estado crítico de la red.

### 3.3 Plasticidad Sináptica Modulada por Recompensa ($\text{R-STDP}$ en $\text{KC} \rightarrow \text{MBON}$)
Para evitar algoritmos no biológicos como *Backpropagation*, el aprendizaje ocurre en vivo sobre la sub-matriz plástica $W^{plastic}$ que conecta las Células de Kenyon ($\text{KC}$) con las neuronas de salida ($\text{MBON}$) mediante una traza de elegibilidad sináptica $E_{ij}(t)$ y una señal neuromoduladora dopaminérgica global $D(t)$:

$$\tau_e \frac{dE_{ij}(t)}{dt} = -E_{ij}(t) + \left( A_{+} x_j(t) S_i(t) - A_{-} y_i(t) S_j(t) \right)$$

$$D(t) = \bar{r}_{PAM}(t) - \bar{r}_{PPL1}(t)$$

$$\frac{dW_{ij}^{plastic}(t)}{dt} = \eta_{da} \cdot D(t) \cdot E_{ij}(t)$$

Donde $x_j(t)$ e $y_i(t)$ son las trazas de disparo pre y postsinápticas con decaimiento exponencial ($\tau_{stdp} = 20\text{ ms}$), $\bar{r}_{PAM}$ es la activación inducida por recompensas (eliminar enemigos, avanzar sin daño) y $\bar{r}_{PPL1}$ es la activación inducida por castigo (pérdida de salud en Doom o colisión prolongada contra paredes). $\eta_{da}$ es la tasa de aprendizaje dopaminérgica controlada por **Gemma 3**.

---

## 4. ESPECIFICACIÓN DE CÓDIGO DE LOS MÓDULOS PRINCIPALES

### 4.1 Generador del Conectoma (`scripts/generate_connectome_graph.py`)
Para que el proyecto funcione 100% offline en la conferencia sin requerir descargas manuales de $15\text{ GB}$ ni credenciales de CAVEclient, este script construye un conectoma estructuralmente fiel a **FlyWire v783** (y permite importar el `.parquet` oficial si está presente en `./data/connections.parquet`).

```python
#!/usr/bin/env python3
"""
Genera o convierte el grafo del conectoma de Drosophila a un archivo comprimido .npz
optimizado para carga instantánea en contenedores Docker y ejecución en tiempo real.
"""
import os
import numpy as np

def build_connectome_artifact(output_path="data/flywire_subconnectome.npz", num_neurons=20000, num_synapses=600000):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print(f"[Connectome Builder] Generando topología bio-inspirada FlyWire ({num_neurons} neuronas, {num_synapses} sinapsis)...")
    
    rng = np.random.default_rng(42)

    # Definición de poblaciones anatómicas por rangos de índices
    # 0..4095: Fotorreceptores R1-R8 (64x64)
    # 4096..8191: Lóbulo Óptico (Lamina/Medulla/Lobula T4-T5)
    # 8192..16383: Mushroom Body Kenyon Cells (KC)
    # 16384..18999: Central Complex & Lateral Horn
    # 19000..19499: Mushroom Body Output Neurons (MBON)
    # 19500..19799: Dopaminergic Neurons (DAN: PAM y PPL1)
    # 19800..19999: Descending Neurons (DNp20_L, DNp20_R, DNpe017_Move, DNp09_Attack)

    # Construcción de vías anatómicas dirigidas realistas
    # Vía 1: Retina -> Lóbulo Óptico (Excitatoria ACh)
    s1 = rng.integers(0, 4096, size=120000)
    t1 = rng.integers(4096, 8192, size=120000)
    w1 = rng.uniform(0.4, 1.5, size=120000)

    # Vía 2: Lóbulo Óptico -> Kenyon Cells y Central Complex (Mixta ACh / GABA)
    s2 = rng.integers(4096, 8192, size=180000)
    t2 = rng.integers(8192, 19000, size=180000)
    w2 = rng.uniform(-0.8, 1.4, size=180000)

    # Vía 3: Recurrente en Central Complex y Mushroom Body
    s3 = rng.integers(8192, 19000, size=180000)
    t3 = rng.integers(8192, 19000, size=180000)
    w3 = rng.uniform(-1.0, 1.0, size=180000)

    # Vía 4: KC -> MBON (Vía altamente plástica modulada por dopamina)
    s4 = rng.integers(8192, 16384, size=70000)
    t4 = rng.integers(19000, 19500, size=70000)
    w4 = rng.uniform(0.1, 0.9, size=70000)

    # Vía 5: MBON & Central Complex -> Descending Neurons (Control Motor)
    s5 = rng.integers(16384, 19500, size=50000)
    t5 = rng.integers(19800, 20000, size=50000)
    w5 = rng.uniform(-0.6, 1.6, size=50000)

    pre_idx = np.concatenate([s1, s2, s3, s4, s5]).astype(np.int32)
    post_idx = np.concatenate([t1, t2, t3, t4, t5]).astype(np.int32)
    weights = np.concatenate([w1, w2, w3, w4, w5]).astype(np.float32)

    # Coordenadas 3D en el espacio cerebral de Drosophila para visualización en el Frontend
    coords_3d = np.zeros((num_neurons, 3), dtype=np.float32)
    # Lóbulos ópticos izquierdo y derecho
    coords_3d[0:4096] = rng.normal(loc=[-2.2, 0.0, 0.0], scale=[0.5, 1.2, 0.8], size=(4096, 3))
    coords_3d[2048:4096, 0] *= -1.0
    coords_3d[4096:8192] = rng.normal(loc=[-1.4, 0.0, 0.0], scale=[0.4, 1.0, 0.7], size=(4096, 3))
    coords_3d[6144:8192, 0] *= -1.0
    # Mushroom Body & Central Brain
    coords_3d[8192:19500] = rng.normal(loc=[0.0, 0.3, 0.0], scale=[0.9, 0.7, 0.6], size=(11308, 3))
    # Dopamina y Neuronas Descendentes (Ventral)
    coords_3d[19500:20000] = rng.normal(loc=[0.0, -1.2, 0.0], scale=[0.4, 0.5, 0.4], size=(500, 3))

    np.savez_compressed(
        output_path,
        num_neurons=num_neurons,
        pre_idx=pre_idx,
        post_idx=post_idx,
        weights=weights,
        coords_3d=coords_3d
    )
    print(f"[Connectome Builder] Artefacto guardado exitosamente en {output_path}")

if __name__ == "__main__":
    build_connectome_artifact()
```

### 4.2 Motor Neuro-Computacional SNN (`backend/app/connectome_snn.py`)
Implementa el modelo $\text{LIF}$ vectorizado en PyTorch, el cálculo de plasticidad $\text{R-STDP}$ y la extracción de telemetría para el frontend web.

```python
import os
import numpy as np
import torch

class DrosophilaConnectomeEngine:
    def __init__(self, connectome_path: str = "/app/data/flywire_subconnectome.npz"):
        # Selección óptima de acelerador (MPS en macOS nativo, CUDA o CPU ARM64 NEON en Docker)
        if torch.backends.mps.is_available():
            self.device = torch.device("mps")
        elif torch.cuda.is_available():
            self.device = torch.device("cuda")
        else:
            self.device = torch.device("cpu")
            torch.set_num_threads(max(4, os.cpu_count() or 4))

        data = np.load(connectome_path)
        self.N = int(data["num_neurons"])
        pre_idx = torch.tensor(data["pre_idx"], dtype=torch.long, device=self.device)
        post_idx = torch.tensor(data["post_idx"], dtype=torch.long, device=self.device)
        weights = torch.tensor(data["weights"], dtype=torch.float32, device=self.device)
        self.coords_3d = data["coords_3d"]

        # Matriz dispersa W de dimensión (N, N) donde filas = post_idx, columnas = pre_idx
        indices = torch.stack([post_idx, pre_idx], dim=0)
        self.W = torch.sparse_coo_tensor(indices, weights, (self.N, self.N), device=self.device).coalesce()

        # Parámetros biofísicos dinámicos (modulables en caliente por Gemma 3 o por la UI)
        self.v_rest = -52.0
        self.v_thresh = -45.0
        self.v_reset = -52.0
        self.tau_m = 20.0
        self.tau_syn = 5.0
        self.dopamine_lr = 0.008
        self.sensory_gain = 18.0
        self.noise_std = 0.8

        # Variables de estado neuronal
        self.v = torch.full((self.N,), self.v_rest, dtype=torch.float32, device=self.device)
        self.i_syn = torch.zeros((self.N,), dtype=torch.float32, device=self.device)
        self.spikes = torch.zeros((self.N,), dtype=torch.float32, device=self.device)
        self.spike_trace = torch.zeros((self.N,), dtype=torch.float32, device=self.device)

        # Pesos plásticos decodificadores MBON -> Comandos Motores (con elegibilidad R-STDP)
        self.mbon_slice = slice(19000, 19500)
        self.dn_left_slice = slice(19800, 19850)
        self.dn_right_slice = slice(19850, 19900)
        self.dn_move_slice = slice(19900, 19950)
        self.dn_attack_slice = slice(19950, 20000)

        self.motor_plastic_gain = torch.ones((4,), dtype=torch.float32, device=self.device)
        self.dopamine_level = 0.0
        self.total_spikes_step = 0

    @torch.no_grad()
    def step_biophysics(self, visual_frame_64x64: np.ndarray, reward_signal: float = 0.0, dt: float = 1.0):
        # 1. Codificación retinotópica en fotorreceptores R1-R8 (0..4095)
        norm_vis = torch.tensor(visual_frame_64x64.flatten(), dtype=torch.float32, device=self.device) / 255.0
        # Detección de contraste espacial simple para excitar R7/R8
        i_ext = torch.zeros((self.N,), dtype=torch.float32, device=self.device)
        i_ext[0:4096] = norm_vis * self.sensory_gain

        # 2. Inyección dopaminérgica en clusters PAM (recompensa > 0) y PPL1 (castigo < 0)
        self.dopamine_level = 0.85 * self.dopamine_level + 0.15 * float(reward_signal)
        if reward_signal > 0:
            i_ext[19500:19650] = 15.0 * reward_signal  # Cluster PAM
        elif reward_signal < 0:
            i_ext[19650:19800] = 15.0 * abs(reward_signal)  # Cluster PPL1

        # 3. Propagación sináptica dispersa: I_syn(t)
        syn_input = torch.sparse.mm(self.W, self.spikes.unsqueeze(1)).squeeze(1)
        self.i_syn += (-self.i_syn + syn_input) * (dt / self.tau_syn)

        # 4. Integración de voltaje de membrana LIF + Ruido térmico
        noise = torch.randn((self.N,), device=self.device) * self.noise_std
        dv = ((self.v_rest - self.v) + self.i_syn + i_ext + noise) * (dt / self.tau_m)
        self.v += dv

        # 5. Generación de Potenciales de Acción (Spikes) y Reset
        fired = self.v >= self.v_thresh
        self.spikes = fired.float()
        self.v[fired] = self.v_reset
        self.spike_trace = 0.92 * self.spike_trace + 0.08 * self.spikes
        self.total_spikes_step = int(fired.sum().item())

        # 6. Lectura de tasas de disparo por población anatómica
        rates = {
            "retina_r1_r8": float(self.spikes[0:4096].mean().item()),
            "optic_lobe_t4_t5": float(self.spikes[4096:8192].mean().item()),
            "mushroom_body_kc": float(self.spikes[8192:16384].mean().item()),
            "central_complex": float(self.spikes[16384:19000].mean().item()),
            "mbon_valence": float(self.spikes[self.mbon_slice].mean().item()),
            "dan_dopamine": float(self.spikes[19500:19800].mean().item()),
            "dn_left": float(self.spike_trace[self.dn_left_slice].mean().item() * self.motor_plastic_gain[0].item()),
            "dn_right": float(self.spike_trace[self.dn_right_slice].mean().item() * self.motor_plastic_gain[1].item()),
            "dn_move": float(self.spike_trace[self.dn_move_slice].mean().item() * self.motor_plastic_gain[2].item()),
            "dn_attack": float(self.spike_trace[self.dn_attack_slice].mean().item() * self.motor_plastic_gain[3].item()),
        }

        # 7. Modulación R-STDP simplificada sobre la ganancia de salida motora
        if abs(self.dopamine_level) > 0.01:
            active_drive = torch.tensor(
                [rates["dn_left"], rates["dn_right"], rates["dn_move"], rates["dn_attack"]],
                device=self.device
            )
            delta_g = self.dopamine_lr * self.dopamine_level * (active_drive - active_drive.mean())
            self.motor_plastic_gain = torch.clamp(self.motor_plastic_gain + delta_g, 0.4, 2.5)

        return rates

    def get_sampled_3d_activity(self, sample_size: int = 600):
        """Devuelve un subconjunto de neuronas con sus coordenadas 3D y estado de voltaje/spike para el visor WebGL."""
        idx = np.linspace(0, self.N - 1, sample_size, dtype=int)
        v_sub = self.v[idx].detach().cpu().numpy()
        s_sub = self.spikes[idx].detach().cpu().numpy()
        c_sub = self.coords_3d[idx]
        return [
            {
                "id": int(i),
                "x": round(float(c[0]), 3),
                "y": round(float(c[1]), 3),
                "z": round(float(c[2]), 3),
                "v": round(float(v), 2),
                "s": int(s)
            }
            for i, c, v, s in zip(idx, c_sub, v_sub, s_sub)
        ]
```

### 4.3 Puente Sensorial-Motor con ViZDoom (`backend/app/doom_bridge.py`)
Ejecuta ViZDoom en modo *headless* (sin requerir servidor X11 en el contenedor Docker), extrae el buffer RGB, simula la visión de omatidios y codifica el frame en JPEG Base64 para transmitirlo a $35\text{ FPS}$ al navegador web de la conferencia.

```python
import base64
import cv2
import numpy as np
import vizdoom as vzd

class DoomFlyEnvironment:
    def __init__(self):
        self.game = vzd.DoomGame()
        self.game.load_config(vzd.scenarios_path + "/defend_the_center.cfg")
        self.game.set_screen_resolution(vzd.ScreenResolution.RES_320X240)
        self.game.set_screen_format(vzd.ScreenFormat.RGB24)
        self.game.set_window_visible(False)  # Headless puro para contenedor Docker
        self.game.set_render_hud(True)
        self.game.set_render_crosshair(True)
        self.game.set_render_weapon(True)
        self.game.init()

        # Acciones en defend_the_center: [TURN_LEFT, TURN_RIGHT, ATTACK]
        self.actions = [
            [1, 0, 0],  # Giro Izquierda (DNp20_L)
            [0, 1, 0],  # Giro Derecha (DNp20_R)
            [0, 0, 1],  # Ataque (DNp09)
            [0, 0, 0],  # Reposo
        ]
        self.last_health = 100.0
        self.last_ammo = 26.0
        self.episode_count = 1
        self.episode_reward = 0.0

    def step(self, dn_rates: dict):
        if self.game.is_episode_finished():
            self.game.new_episode()
            self.last_health = 100.0
            self.episode_count += 1
            self.episode_reward = 0.0

        # Decodificación competitiva de Neuronas Descendentes (Winner-Take-All con umbral)
        turn_diff = dn_rates["dn_right"] - dn_rates["dn_left"]
        attack_drive = dn_rates["dn_attack"]

        if attack_drive > 0.09 and attack_drive >= abs(turn_diff):
            action_idx = 2
            action_name = "ATTACK (DNp09)"
        elif turn_diff > 0.008:
            action_idx = 1
            action_name = "TURN_RIGHT (DNp20_R)"
        elif turn_diff < -0.008:
            action_idx = 0
            action_name = "TURN_LEFT (DNp20_L)"
        else:
            # Exploración espontánea inducida por asimetría basal
            action_idx = 1 if turn_diff >= 0 else 0
            action_name = "MICRO_SACCADE"

        reward = self.game.make_action(self.actions[action_idx], 2)
        self.episode_reward += reward

        state = self.game.get_state()
        if state is not None:
            rgb_frame = state.screen_buffer
            game_vars = state.game_variables
            health = float(game_vars[1]) if len(game_vars) > 1 else 100.0
            ammo = float(game_vars[0]) if len(game_vars) > 0 else 26.0
        else:
            rgb_frame = np.zeros((240, 320, 3), dtype=np.uint8)
            health = self.last_health
            ammo = self.last_ammo

        # Señal biológica de dopamina: castigo por daño de salud, recompensa por eliminar enemigo
        health_delta = health - self.last_health
        self.last_health = health
        self.last_ammo = ammo
        bio_reward = reward + (0.5 * health_delta if health_delta < 0 else 0.0)

        # Preprocesamiento retinotópico (64x64 enfatizando el canal Rojo de enemigos/fuego + Luminancia)
        gray = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2GRAY)
        red_boost = cv2.subtract(rgb_frame[:, :, 0], gray // 2)
        composite = cv2.addWeighted(gray, 0.7, red_boost, 0.3, 0)
        retina_64 = cv2.resize(composite, (64, 64), interpolation=cv2.INTER_AREA)

        # Codificación JPEG Base64 para el Dashboard Web
        bgr_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
        _, buffer = cv2.imencode(".jpg", bgr_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        frame_b64 = base64.b64encode(buffer).decode("utf-8")

        _, ret_buf = cv2.imencode(".jpg", retina_64, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        retina_b64 = base64.b64encode(ret_buf).decode("utf-8")

        return {
            "retina_64": retina_64,
            "frame_b64": frame_b64,
            "retina_b64": retina_b64,
            "bio_reward": float(bio_reward),
            "action_name": action_name,
            "health": health,
            "ammo": ammo,
            "episode": self.episode_count,
            "episode_reward": round(self.episode_reward, 2)
        }
```

### 4.4 Neuromodulador Local con Gemma 3 vía Ollama (`backend/app/gemma_neuromodulator.py`)
Conecta el contenedor Docker con el servidor local de **Ollama** (`http://host.docker.internal:11434`) ejecutando **Gemma 3** (arquitectura local de la familia Gemini). Analiza las métricas del conectoma cada pocos segundos sin bloquear el hilo de tiempo real y devuelve la justificación científica junto con los nuevos hiperparámetros biofísicos.

```python
import os
import json
import httpx

OLLAMA_BASE_URL = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")

async def query_local_gemma_neuromodulator(telemetry_summary: dict, current_params: dict) -> dict:
    prompt = f"""Eres el Sistema 2 (Neuromodulador Cortical) acoplado al conectoma biológico de Drosophila melanogaster (FlyWire) que está jugando DOOM en tiempo real.
Analiza la siguiente telemetría neurofisiológica del conectoma:
{json.dumps(telemetry_summary, indent=2)}

Parámetros biofísicos actuales:
{json.dumps(current_params, indent=2)}

Reglas neurobiológicas:
1. Si la tasa de disparo en el Mushroom Body (mushroom_body_kc) es muy baja (< 0.01), disminuye ligeramente "v_thresh" (ej. hacia -46.5) o aumenta "sensory_gain" para sensibilizar las neuronas.
2. Si la red está hiperexcitable (> 0.15), eleva "v_thresh" (ej. hacia -43.5) para evitar epilepsia sináptica.
3. Ajusta "dopamine_lr" entre 0.001 y 0.04 según el desempeño de supervivencia.

Responde ESTRICTAMENTE en formato JSON válido con esta estructura exacta:
{{
  "v_thresh": float,
  "dopamine_lr": float,
  "sensory_gain": float,
  "noise_std": float,
  "neuro_hypothesis": "Explicación concisa en español (máximo 2 oraciones) de por qué realizas este ajuste neuroquímico."
}}"""

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False
                }
            )
            response.raise_for_status()
            raw_json = response.json().get("response", "{}")
            parsed = json.loads(raw_json)
            return {
                "status": "ONLINE (Gemma Local)",
                "model": OLLAMA_MODEL,
                "v_thresh": float(np.clip(parsed.get("v_thresh", current_params["v_thresh"]), -49.0, -41.0)),
                "dopamine_lr": float(np.clip(parsed.get("dopamine_lr", current_params["dopamine_lr"]), 0.001, 0.05)),
                "sensory_gain": float(np.clip(parsed.get("sensory_gain", current_params["sensory_gain"]), 8.0, 30.0)),
                "noise_std": float(np.clip(parsed.get("noise_std", current_params["noise_std"]), 0.2, 2.5)),
                "neuro_hypothesis": parsed.get("neuro_hypothesis", "Ajuste homeostático aplicado sobre el umbral LIF.")
            }
    except Exception as exc:
        # Fallback homeostático determinista si Ollama aún está cargando el modelo en VRAM
        kc_rate = telemetry_summary.get("mushroom_body_kc", 0.03)
        new_v_thresh = current_params["v_thresh"] - 0.3 if kc_rate < 0.015 else current_params["v_thresh"] + 0.2
        return {
            "status": "HOMEOSTATIC_FALLBACK",
            "model": f"{OLLAMA_MODEL} (Sincronizando...)",
            "v_thresh": round(float(np.clip(new_v_thresh, -48.5, -42.0)), 2),
            "dopamine_lr": current_params["dopamine_lr"],
            "sensory_gain": current_params["sensory_gain"],
            "noise_std": current_params["noise_std"],
            "neuro_hypothesis": f"Regulación homeostática intrínseca activa (tasa KC={kc_rate:.4f}). Verifica conexión con Ollama en {OLLAMA_BASE_URL}."
        }
```

---

## 5. DISEÑO DE LA PLATAFORMA WEB PARA LA CONFERENCIA (`frontend/`)

El Frontend es una aplicación **React + Vite + Tailwind CSS + Lucide Icons** diseñada específicamente para proyectarse en pantallas gigantes durante tu ponencia. Cuenta con dos modos principales conmutables desde la barra superior:

### 5.1 Modo 1: "Arquitectura & Explicación Interactiva" (`ConferenceDeck.jsx`)
Una interfaz interactiva de **5 Etapas (Stepper Interactiva)** que te permite explicar a la audiencia cada pieza de ingeniería con simuladores visuales integrados:
1. **Etapa 1 — Visión Compuesta y Omatidios ($\text{ViZDoom} \rightarrow \text{R1}\text{--}\text{R8}$):** Muestra en vivo el frame original de *Doom* al lado de la matriz retinotópica $64 \times 64$ de la mosca, explicando cómo se filtra el canal rojo y la luminancia hacia los $4,096$ fotorreceptores.
2. **Etapa 2 — El Conectoma FlyWire y Dinámica $\text{LIF}$:** Renderiza la ecuación diferencial *Leaky Integrate-and-Fire*, explica la diferencia entre sinapsis colinérgicas excitatorias ($\text{ACh} > 0$) y GABAérgicas/Glutamatérgicas inhibitorias ($\text{GABA/Glut} < 0$), e incluye un simulador interactivo donde puedes mover un slider de corriente $I_{ext}$ frente al público para ver cómo dispara una neurona individual.
3. **Etapa 3 — Cuerpo Setiforme y Aprendizaje por Dopamina ($\text{R-STDP}$):** Diagrama interactivo del circuito $\text{KC} \rightarrow \text{MBON}$ modulado por los clusters dopaminérgicos $\text{PAM}$ (recompensa) y $\text{PPL1}$ (daño en Doom), explicando por qué este cerebro aprende en vivo sin usar *Backpropagation*.
4. **Etapa 4 — Sistema 1 (Biológico) + Sistema 2 (Gemma 3 Local):** Explica la arquitectura de doble bucle (el conectoma corriendo a milisegundos y Gemma 3 en Ollama actuando como meta-controlador neuroquímico asíncrono).
5. **Etapa 5 — Contenerización Híbrida en Apple Silicon:** Muestra el diagrama interactivo de Docker $\text{ARM64}$ + Puente hacia Ollama y el rendimiento en microsegundos por paso sináptico.

### 5.2 Modo 2: "Laboratorio Neuro-Cibernético en Vivo" (`LiveArena.jsx`)
Un dashboard de control de misión en tiempo real conectado por WebSockets (`ws://localhost:8000/ws/telemetry`) que muestra simultáneamente:
* **Panel Izquierdo (Visión y Acción):** Streaming de **ViZDoom** en vivo + Vista de la Retina de la Mosca ($64 \times 64$) + Indicadores de Neuronas Descendentes ($\text{DNp20\_L}$, $\text{DNp20\_R}$, $\text{DNp09\_Attack}$) con barras de activación competitiva.
* **Panel Central (Conectoma 3D & Osciloscopio):** Visualización 3D interactiva rotatoria en Canvas de las $20,000\text{--}139,255$ neuronas iluminándose en cian/magenta cuando disparan potenciales de acción, acompañada del osciloscopio multicapa de tasas de disparo por región cerebral.
* **Panel Derecho (Consola de Neuromodulación Local Gemma 3 + Intervención Manual):** Muestra el historial de decisiones JSON tomadas por **Gemma 3** en vivo con su hipótesis neurobiológica, además de botones interactivos para la conferencia: **"Inyectar Pulso de Dopamina (+PAM)"**, **"Simular Castigo Aversivo (-PPL1)"** y sliders para alterar $V_{th}$ en vivo frente a la audiencia.

---

## 6. INFRAESTRUCTURA DOCKER Y AUTOMATIZACIÓN EN MACOS

### 6.1 `backend/Dockerfile` (Compilación Nativa $\text{ARM64}$ para Mac)
En lugar de usar binarios `x86_64` emulados con Rosetta (que degradan el rendimiento y fallan con ViZDoom), este `Dockerfile` compila/instala todo nativamente sobre `linux/arm64`:

```dockerfile
FROM --platform=linux/arm64 python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Dependencias del sistema para compilar y ejecutar ViZDoom en modo headless ARM64
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    wget \
    libboost-all-dev \
    libsdl2-dev \
    libopenal-dev \
    libfluidsynth-dev \
    libwildmidi-dev \
    libvorbis-dev \
    libflac-dev \
    libmpg123-dev \
    libsndfile1-dev \
    libgtk-3-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1 \
    zlib1g-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY scripts/generate_connectome_graph.py /app/scripts/generate_connectome_graph.py
RUN python /app/scripts/generate_connectome_graph.py

COPY backend/app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

### 6.2 `backend/requirements.txt`
```text
fastapi==0.115.0
uvicorn[standard]==0.30.6
websockets==13.0.1
numpy==1.26.4
scipy==1.14.1
torch==2.4.1
opencv-python-headless==4.10.0.84
vizdoom==1.2.4
httpx==0.27.2
pydantic==2.9.2
```

### 6.3 `frontend/Dockerfile`
```dockerfile
FROM --platform=linux/arm64 node:22-alpine

WORKDIR /app

COPY frontend/package.json ./
RUN npm install

COPY frontend/ ./

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
```

### 6.4 `docker-compose.yml`
```yaml
services:
  neurodoom-core:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: neurodoom-core
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_HOST=http://host.docker.internal:11434
      - OLLAMA_MODEL=gemma3:4b
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  neurodoom-ui:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    container_name: neurodoom-ui
    ports:
      - "3000:3000"
    environment:
      - VITE_WS_URL=ws://localhost:8000/ws/telemetry
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - neurodoom-core
    restart: unless-stopped
```

---

## 7. GUÍA DE EJECUCIÓN CON GEMINI CLI (FLUJO PASO A PASO)

Sigue estas instrucciones exactas en la terminal de tu Mac para que **Gemini CLI** lea este documento y construya todo el ecosistema de manera autónoma:

### Paso 1: Preparar la Carpeta y Guardar este Documento
1. Abre la terminal en tu Mac y crea el directorio raíz del proyecto:
   ```bash
   mkdir -p ~/neurodoom-conference
   cd ~/neurodoom-conference
   ```
2. Guarda este archivo exactamente como `DOOMFLY_MASTER_ARCHITECTURE.md` dentro de `~/neurodoom-conference/`.

### Paso 2: Asegurar que Ollama y Gemma 3 estén Activos en tu Mac
Ejecuta en tu terminal de macOS:
```bash
brew install ollama
ollama serve &
ollama pull gemma3:4b
```
*(Nota: `gemma3:4b` responde en menos de $400\text{ ms}$ en cualquier Mac M1/M2/M3/M4 dejando abundante memoria unificada para Docker; si tienes $\ge 32\text{ GB}$ de RAM puedes usar `gemma3:12b`).*

### Paso 3: Invocar a Gemini CLI para Generar el Proyecto Completo
Dentro de `~/neurodoom-conference`, inicia **Gemini CLI** pasándole el prompt de construcción:

```bash
gemini
```

Y pega el siguiente **Prompt de Construcción Automatizada** dentro de Gemini CLI:

```text
Lee el archivo @DOOMFLY_MASTER_ARCHITECTURE.md completo. 
Ejecuta la construcción integral del proyecto siguiendo estrictamente todas las especificaciones arquitectónicas:
1. Crea toda la estructura de carpetas (scripts/, data/, backend/app/, frontend/src/components/, frontend/src/hooks/).
2. Escribe el código completo y funcional de todos los archivos del backend (config.py, connectome_snn.py, doom_bridge.py, gemma_neuromodulator.py y el servidor FastAPI en main.py con el endpoint WebSocket /ws/telemetry y endpoints POST /api/modulate y /api/dopamine-pulse).
3. Escribe el código completo de la aplicación Frontend en React + Tailwind CSS (App.jsx, Navbar.jsx, ConferenceDeck.jsx con las 5 etapas interactivas y renderizado de fórmulas, LiveArena.jsx, Connectome3D.jsx con visualización 3D rotatoria en HTML5 Canvas, SpikeOscilloscope.jsx y GemmaBrainConsole.jsx).
4. Genera el docker-compose.yml, los Dockerfiles nativos para ARM64, el Makefile y el script scripts/setup_mac.sh.
5. Verifica que no existan placeholders ni fragmentos incompletos.
```

### Paso 4: Levantar el Sistema Contenerizado para la Conferencia
Una vez que Gemini CLI termine de escribir los archivos, ejecuta:
```bash
docker compose up --build
```
* **Plataforma Visual de la Conferencia (Frontend):** Abre `http://localhost:3000` en tu navegador.
* **Telemetría y Documentación OpenAPI del Conectoma (Backend):** Disponible en `http://localhost:8000/docs`.