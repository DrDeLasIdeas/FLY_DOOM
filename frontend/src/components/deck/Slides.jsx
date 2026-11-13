import React from "react";
import {
  Activity,
  Award,
  Cpu,
  Eye,
  Layers,
  Lightbulb,
  Radio,
  Sparkles,
} from "lucide-react";
import Equation from "./Equation.jsx";
import RetinaWidget from "./RetinaWidget.jsx";
import LifWidget from "./LifWidget.jsx";
import PlasticityWidget from "./PlasticityWidget.jsx";
import GemmaWidget from "./GemmaWidget.jsx";
import RuntimeWidget from "./RuntimeWidget.jsx";

function Metric({ label, value, tone = "text-cyan-300" }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/80 px-3 py-2.5">
      <div className="font-mono text-[10px] sm:text-xs uppercase tracking-wider text-slate-400">{label}</div>
      <div className={`font-mono text-base sm:text-lg font-bold ${tone}`}>{value}</div>
    </div>
  );
}

function Metrics({ items }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
      {items.map((item) => (
        <Metric key={item.label} {...item} />
      ))}
    </div>
  );
}

function Bullets({ items, presenting }) {
  return (
    <ul className={`space-y-2.5 ${presenting ? "text-base lg:text-lg" : "text-sm sm:text-base"} text-slate-200`}>
      {items.map((item) => (
        <li key={item} className="flex gap-2.5">
          <span className="mt-2 w-1.5 h-1.5 rounded-full bg-cyan-400 shrink-0" />
          <span className="leading-relaxed">{item}</span>
        </li>
      ))}
    </ul>
  );
}

function Why({ children }) {
  return (
    <div className="rounded-xl border border-fuchsia-500/30 bg-fuchsia-950/20 p-4">
      <div className="flex items-center gap-1.5 font-mono text-xs uppercase tracking-wider text-fuchsia-300 mb-1.5">
        <Lightbulb className="w-4 h-4" /> Por qué se diseñó así
      </div>
      <p className="text-sm sm:text-base leading-relaxed text-fuchsia-100/95">{children}</p>
    </div>
  );
}

function Live({ items }) {
  return (
    <div className="flex flex-wrap gap-2 font-mono text-xs">
      {items.map((item) => (
        <span
          key={item.label}
          className="px-2.5 py-1.5 rounded-lg border border-slate-700 bg-slate-950 text-slate-400"
        >
          {item.label} <strong className="text-slate-100">{item.value ?? "—"}</strong>
        </span>
      ))}
    </div>
  );
}

function SlideGrid({ widget, side, presenting }) {
  return (
    <div
      className={`grid grid-cols-1 ${
        presenting ? "xl:grid-cols-[minmax(0,1.35fr)_minmax(0,0.65fr)]" : "xl:grid-cols-[minmax(0,1.3fr)_minmax(0,0.7fr)]"
      } gap-5`}
    >
      <div className="space-y-3 min-w-0">{widget}</div>
      <div className="space-y-3 min-w-0">{side}</div>
    </div>
  );
}

export function VisionSlide({ telemetry, presenting }) {
  return (
    <div className="space-y-4">
      <p className={`leading-relaxed text-slate-100 ${presenting ? "text-lg lg:text-xl" : "text-base lg:text-lg"}`}>
        El buffer RGB de ViZDoom (320×240) se proyecta sobre una retina virtual de{" "}
        <strong className="text-cyan-300">64×64 = 4,096 omatidios</strong>. La luminancia y el canal
        rojo se combinan con una PSF gaussiana y una ganancia sensorial; el resultado es una corriente
        externa retinotópica que alimenta la lámina y la médula óptica.
      </p>

      <Equation
        label="Corriente externa retinotópica"
        tex={String.raw`I^{\mathrm{ext}}_i(t)=g_s\left(0.7\,\frac{L_i}{255}+0.3\,\frac{R_i}{255}\right)\exp\!\left(-\frac{\lVert p_i-p_s(t)\rVert^2}{2\sigma^2}\right)`}
      />

      <Metrics
        items={[
          { label: "omatidios", value: "4,096", tone: "text-cyan-300" },
          { label: "resolución", value: "64×64", tone: "text-emerald-300" },
          { label: "ojos", value: "32 + 32", tone: "text-violet-300" },
          { label: "stream", value: "35 Hz", tone: "text-amber-300" },
          { label: "g_sensorial", value: telemetry?.biophysics?.sensory_gain ?? 18, tone: "text-rose-300" },
          { label: "canales", value: "R1–R8", tone: "text-slate-200" },
        ]}
      />

      <SlideGrid
        presenting={presenting}
        widget={<RetinaWidget telemetry={telemetry} />}
        side={
          <>
            <Bullets
              presenting={presenting}
              items={[
                "R1–R6 codifican luminancia; R7–R8 aportan el canal rojo asociado a amenazas y sangre.",
                "La proyección conserva la vecindad espacial: cada omatidio mantiene su posición retinotópica.",
                "Las neuronas T4/T5 de la médula estiman movimiento local; el conectoma recibe 4,096 corrientes externas independientes.",
                "El submuestreo con PSF gaussiana evita aliasing cuando el buffer de DOOM cambia de resolución.",
              ]}
            />
            <Live
              items={[
                { label: "acción", value: telemetry?.action_name },
                { label: "KC rate", value: telemetry?.rates?.mushroom_body_kc },
                { label: "episodio", value: telemetry?.episode },
              ]}
            />
            <Why>
              El ojo compuesto de <em>Drosophila</em> tiene ~750 omatidios por ojo. La retina virtual
              preserva la topología del conectoma FlyWire sin cargar una imagen de alta resolución en
              cada paso de 1 ms.
            </Why>
          </>
        }
      />
    </div>
  );
}

export function LifSlide({ telemetry, presenting }) {
  return (
    <div className="space-y-4">
      <p className={`leading-relaxed text-slate-100 ${presenting ? "text-lg lg:text-xl" : "text-base lg:text-lg"}`}>
        Cada una de las <strong className="text-cyan-300">20,000 neuronas</strong> integra corriente
        sináptica y externa con una dinámica leaky integrate-and-fire. El frame de 1 ms se divide en{" "}
        <strong className="text-cyan-300">4 sub-pasos de 0.25 ms</strong> y la matriz sináptica se
        mantiene en formato disperso COO/CSR.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Equation
          label="Membrana LIF"
          tex={String.raw`\tau_m\frac{dV_i}{dt}=-(V_i-V_{\mathrm{rest}})+R\,I_i^{\mathrm{syn}}(t)+R\,I_i^{\mathrm{ext}}(t)+\sigma\sqrt{\tau_m}\,\xi_i(t)`}
        />
        <Equation
          label="Corriente sináptica dispersa"
          tex={String.raw`\tau_s\frac{dI_i^{\mathrm{syn}}}{dt}=-I_i^{\mathrm{syn}}+\sum_{j\in\mathcal{N}(i)}W_{ij}\,s_j(t),\qquad V_i\leftarrow V_{\mathrm{reset}}\ \text{si}\ V_i\ge V_{th}`}
        />
      </div>

      <Metrics
        items={[
          { label: "neuronas", value: "20,000", tone: "text-cyan-300" },
          { label: "sinapsis", value: "600k", tone: "text-violet-300" },
          { label: "V_rest", value: `${telemetry?.biophysics?.v_rest ?? -52} mV`, tone: "text-slate-200" },
          { label: "V_th", value: `${telemetry?.biophysics?.v_thresh ?? -45} mV`, tone: "text-amber-300" },
          { label: "τ_m / τ_syn", value: "20 / 5 ms", tone: "text-emerald-300" },
          { label: "sub-pasos", value: telemetry?.biophysics?.substeps ?? 4, tone: "text-rose-300" },
        ]}
      />

      <SlideGrid
        presenting={presenting}
        widget={<LifWidget telemetry={telemetry} />}
        side={
          <>
            <Bullets
              presenting={presenting}
              items={[
                "El disparo resetea V a −58 mV y aplica 2 ms de refractario, evitando ráfagas no biológicas.",
                "La suma sináptica usa torch.sparse.mm; W nunca se densifica, incluso en el fallback CPU.",
                "MPS de Apple no soporta COO disperso: el backend cae a CPU NEON sin cambiar la semántica.",
                "El ruido ξ_i(t) mantiene el régimen subumbral y evita sincronía artificial.",
              ]}
            />
            <Live
              items={[
                { label: "latencia", value: `${telemetry?.biophysics?.latency_ms ?? "—"} ms` },
                { label: "spikes", value: telemetry?.biophysics?.total_spikes },
                { label: "device", value: telemetry?.biophysics?.device ?? "cpu" },
              ]}
            />
            <Why>
              Una SNN transmite información por eventos binarios dispersos. El costo energético depende
              de los spikes, no de multiplicar una matriz densa en cada paso.
            </Why>
          </>
        }
      />
    </div>
  );
}

export function PlasticitySlide({ telemetry, presenting, onDopaminePulse }) {
  return (
    <div className="space-y-4">
      <p className={`leading-relaxed text-slate-100 ${presenting ? "text-lg lg:text-xl" : "text-base lg:text-lg"}`}>
        Las células de Kenyon (KC) del cuerpo setiforme proyectan hacia las neuronas de salida (MBON).
        Las neuronas dopaminérgicas <strong className="text-emerald-300">PAM</strong> (recompensa) y{" "}
        <strong className="text-rose-300">PPL1</strong> (castigo) emiten el tercer factor que modula
        trazas de elegibilidad locales: no hay backpropagation global.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Equation
          label="Regla de tres factores R-STDP"
          tex={String.raw`E_{ij}\leftarrow \lambda E_{ij}+s_i^{\mathrm{pre}}s_j^{\mathrm{post}},\qquad \Delta W_{ij}=\eta_{DA}(t)\,E_{ij}(t)`}
        />
        <Equation
          label="Señal dopaminérgica"
          tex={String.raw`\eta_{DA}(t)=\eta_0\left(\bar r_{\mathrm{PAM}}(t)-\bar r_{\mathrm{PPL1}}(t)\right),\qquad W_{ij}\leftarrow \mathrm{clip}(W_{ij},0,1)`}
        />
      </div>

      <Metrics
        items={[
          { label: "KC visibles", value: "900", tone: "text-cyan-300" },
          { label: "MBON", value: "500", tone: "text-violet-300" },
          { label: "DAN", value: "300", tone: "text-amber-300" },
          { label: "η_da", value: telemetry?.gemma?.dopamine_lr ?? "—", tone: "text-emerald-300" },
          { label: "λ", value: "0.90", tone: "text-fuchsia-300" },
          { label: "dopamina", value: telemetry?.biophysics?.dopamine_level ?? "—", tone: "text-rose-300" },
        ]}
      />

      <SlideGrid
        presenting={presenting}
        widget={
          <PlasticityWidget telemetry={telemetry} onDopaminePulse={onDopaminePulse} />
        }
        side={
          <>
            <Bullets
              presenting={presenting}
              items={[
                "El acierto de un disparo o una baja incrementa la recompensa y activa PAM.",
                "El daño recibido activa PPL1 y empuja la traza de elegibilidad en sentido negativo.",
                "La elegibilidad decae exponencialmente: solo las sinapsis activas recientemente se modifican.",
                "El peso se recorta a [0,1] para mantener estabilidad numérica y evitar saturación.",
              ]}
            />
            <Live
              items={[
                { label: "recompensa", value: telemetry?.shaped_reward },
                { label: "KC rate", value: telemetry?.rates?.mushroom_body_kc },
                { label: "DA", value: telemetry?.biophysics?.dopamine_level },
              ]}
            />
            <Why>
              La dopamina actúa como predicción de recompensa: no dice qué peso cambiar, solo modula la
              magnitud y el signo de cambios ya elegidos por la correlación pre/postsináptica.
            </Why>
          </>
        }
      />
    </div>
  );
}

export function HybridSlide({ telemetry, presenting }) {
  return (
    <div className="space-y-4">
      <p className={`leading-relaxed text-slate-100 ${presenting ? "text-lg lg:text-xl" : "text-base lg:text-lg"}`}>
        El conectoma corre el bucle rápido (<strong className="text-cyan-300">Sistema 1</strong>) cada
        milisegundo. Gemma 3 en Ollama analiza la telemetría cada{" "}
        <strong className="text-fuchsia-300">5 segundos</strong> (<strong>Sistema 2</strong>) y propone
        parámetros homeostáticos. El backend aplica un clamp duro y nunca bloquea el WebSocket.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Equation
          label="Clamp homeostático"
          tex={String.raw`V_{th}^{t+1}=\Pi_{[-49,\,-41]}\Big(\mathrm{Gemma}_3\big(\mathcal{T}_t\big)\Big),\qquad \Pi_{[a,b]}(x)=\min\{b,\max\{a,x\}\}`}
        />
        <Equation
          label="Desacoplamiento temporal"
          tex={String.raw`\Delta t_{\mathrm{SNN}}=1\,\mathrm{ms}\ \ll\ T_{\mathrm{Gemma}}=5\,\mathrm{s}\ \Rightarrow\ \text{background task asíncrona}`}
        />
      </div>

      <Metrics
        items={[
          { label: "periodo Gemma", value: "5 s", tone: "text-fuchsia-300" },
          { label: "timeout", value: "6 s", tone: "text-amber-300" },
          { label: "clamp", value: "[-49,-41]", tone: "text-cyan-300" },
          { label: "modelo", value: telemetry?.gemma?.model ?? "gemma3:4b", tone: "text-emerald-300" },
          { label: "stream", value: "35 Hz", tone: "text-violet-300" },
          { label: "bloqueo WS", value: "0 ms", tone: "text-rose-300" },
        ]}
      />

      <SlideGrid
        presenting={presenting}
        widget={<GemmaWidget telemetry={telemetry} />}
        side={
          <>
            <Bullets
              presenting={presenting}
              items={[
                "Sistema 1: reacción rápida, determinista y de bajo nivel (SNN + política motora).",
                "Sistema 2: razonamiento lento sobre tasas y recompensa, sin tocar el bucle de 35 Hz.",
                "Si Ollama no responde, entra un fallback homeostático intrínseco y el juego continúa.",
                "El clamp evita silencio sináptico e hiperexcitabilidad epiléptica.",
              ]}
            />
            <Live
              items={[
                { label: "V_th", value: `${telemetry?.biophysics?.v_thresh ?? "—"} mV` },
                { label: "Gemma", value: telemetry?.gemma?.status ?? "—" },
                { label: "latencia", value: `${telemetry?.biophysics?.latency_ms ?? "—"} ms` },
              ]}
            />
            <Why>
              El bucle de telemetría es sagrado: Gemma corre en una tarea de fondo y publica su estado
              más reciente. El conectoma nunca espera a un modelo de lenguaje.
            </Why>
          </>
        }
      />
    </div>
  );
}

export function RuntimeSlide({ telemetry, presenting }) {
  return (
    <div className="space-y-4">
      <p className={`leading-relaxed text-slate-100 ${presenting ? "text-lg lg:text-xl" : "text-base lg:text-lg"}`}>
        ViZDoom, PyTorch sparse y FastAPI corren en contenedores{" "}
        <strong className="text-cyan-300">linux/arm64</strong>; Ollama usa Metal en el host. El
        presupuesto por paso se mantiene por debajo de 15 ms y la matriz dispersa reduce la memoria de{" "}
        <strong className="text-rose-300">1.6 GB</strong> a{" "}
        <strong className="text-emerald-300">~12 MB</strong>.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Equation
          label="Costo de memoria"
          tex={String.raw`M_{\mathrm{dense}}=N^2b=(2\cdot10^4)^2\cdot4\,\mathrm{B}=1.6\,\mathrm{GB}`}
        />
        <Equation
          label="Formato disperso"
          tex={String.raw`M_{\mathrm{sparse}}=nnz\,(b_v+2b_i)\approx 6\cdot10^5\cdot20\,\mathrm{B}=12\,\mathrm{MB}\quad(\times 133)`}
        />
      </div>

      <Metrics
        items={[
          { label: "W densa", value: "1.6 GB", tone: "text-rose-300" },
          { label: "W COO", value: "~12 MB", tone: "text-emerald-300" },
          { label: "compresión", value: "133×", tone: "text-cyan-300" },
          { label: "latencia", value: `${telemetry?.biophysics?.latency_ms ?? 4.6} ms`, tone: "text-amber-300" },
          { label: "stream", value: "35 Hz", tone: "text-violet-300" },
          { label: "target", value: "ARM64", tone: "text-slate-200" },
        ]}
      />

      <SlideGrid
        presenting={presenting}
        widget={<RuntimeWidget telemetry={telemetry} />}
        side={
          <>
            <Bullets
              presenting={presenting}
              items={[
                "Docker multi-arquitectura garantiza el mismo entorno en Apple Silicon y en el servidor.",
                "Metal se reserva para Gemma 3; el conectoma usa CPU NEON para sparse mm.",
                "La matriz W se serializa como COO y se mantiene dispersa en todo el pipeline.",
                "Un solo comando levanta el stack; los servicios nativos se detienen con kill -9.",
              ]}
            />
            <Live
              items={[
                { label: "device", value: telemetry?.biophysics?.device ?? "cpu" },
                { label: "latencia", value: `${telemetry?.biophysics?.latency_ms ?? "—"} ms` },
                { label: "bajas", value: telemetry?.total_kills ?? 0 },
              ]}
            />
            <Why>
              Densificar W no solo desperdicia memoria: destruye la localidad de caché y vuelve
              inviable el bucle de 1 ms. La representación dispersa es una decisión de arquitectura,
              no una optimización opcional.
            </Why>
          </>
        }
      />
    </div>
  );
}

export const SLIDES = [
  {
    id: 1,
    short: "Retina compuesta",
    title: "Codificación retinotópica del ojo compuesto",
    badge: "ViZDoom 320×240 → 64×64 omatidios",
    icon: Eye,
    accent: "cyan",
    Component: VisionSlide,
    notes: [
      "Enfatizar que 4,096 no es una imagen: es un vector de corrientes externas con topología retinotópica.",
      "La PSF gaussiana explica por qué un estímulo puntual activa un vecindario de omatidios, no un solo píxel.",
      "R1–R6 son sensores de luminancia de banda ancha; R7–R8 aportan información espectral y de amenaza.",
      "Conectar con la lámina y la médula: T4/T5 detectan movimiento local y alimentan vías descendentes.",
    ],
    refs: [
      "Dorkenwald et al. (2024). Neuronal wiring diagram of an adult brain. Nature 634, 124–138.",
      "Borst & Euler (2011). Seeing things in motion: models, circuits, and mechanisms. Neuron 71, 974–994.",
      "Wydmuch et al. (2019). ViZDoom: A Doom-based AI research platform. IEEE T-CIAIG.",
    ],
  },
  {
    id: 2,
    short: "LIF disperso",
    title: "Dinámica LIF y sinapsis dispersas",
    badge: "20,000 neuronas · 600k sinapsis · 4 sub-pasos",
    icon: Activity,
    accent: "emerald",
    Component: LifSlide,
    notes: [
      "Recalcar la diferencia entre ANN densa y SNN: eventos binarios vs multiplicaciones densas.",
      "El sub-paso de 0.25 ms estabiliza la integración numérica sin cambiar la escala biológica del frame.",
      "El refractario de 2 ms evita que una neurona dispare varias veces en el mismo sub-paso.",
      "MPS no soporta COO; el fallback CPU NEON es una decisión de portabilidad, no un parche.",
    ],
    refs: [
      "Gerstner & Kistler (2002). Spiking Neuron Models. Cambridge University Press.",
      "PyTorch Foundation. Sparse COO/CSR tensor documentation.",
      "Dorkenwald et al. (2024). FlyWire connectome. Nature 634, 124–138.",
    ],
  },
  {
    id: 3,
    short: "R-STDP / PAM",
    title: "Cuerpo setiforme, PAM/PPL1 y R-STDP",
    badge: "Aprendizaje local de tres factores",
    icon: Award,
    accent: "violet",
    Component: PlasticitySlide,
    notes: [
      "La regla tiene tres factores: pre, post y dopamina. No hay señal de error global.",
      "PAM y PPL1 son poblaciones dopaminérgicas distintas; su diferencia codifica el signo del aprendizaje.",
      "La traza de elegibilidad resuelve el problema de crédito temporal sin backpropagation.",
      "El clip [0,1] mantiene estabilidad; en biología la fuerza sináptica también tiene límites.",
    ],
    refs: [
      "Schultz (1998). Predictive reward signal of dopamine neurons. J. Neurophysiol. 80, 1–27.",
      "Frémaux & Gerstner (2016). Neuromodulated STDP and theory of three-factor learning rules. Front. Neural Circuits 9, 85.",
      "Cognigni et al. (2018). Do the right thing: neural network mechanisms of memory and decision. Curr. Biol.",
    ],
  },
  {
    id: 4,
    short: "Sistema 1 + 2",
    title: "Doble sistema: SNN 1 ms + Gemma 3 asíncrono",
    badge: "Sistema 1 rápido + Sistema 2 homeostático",
    icon: Cpu,
    accent: "fuchsia",
    Component: HybridSlide,
    notes: [
      "Kahneman: Sistema 1 rápido e intuitivo; Sistema 2 lento y deliberado. Aquí se implementa con dos relojes.",
      "Gemma no controla directamente los motores: propone parámetros que el backend recorta.",
      "El clamp [-49,-41] mV es una garantía de seguridad fisiológica, no una sugerencia del modelo.",
      "El WebSocket de 35 Hz jamás espera a Ollama; el estado de Gemma se publica cuando está listo.",
    ],
    refs: [
      "Kahneman (2011). Thinking, Fast and Slow. Farrar, Straus and Giroux.",
      "Gemma Team (2025). Gemma 3 technical report. Google DeepMind.",
      "Ollama documentation. Local model serving and JSON mode.",
    ],
  },
  {
    id: 5,
    short: "Runtime ARM64",
    title: "Orquestación ARM64 y presupuesto de latencia",
    badge: "Docker linux/arm64 + Metal host",
    icon: Layers,
    accent: "amber",
    Component: RuntimeSlide,
    notes: [
      "La comparación 1.6 GB vs 12 MB es el argumento más contundente contra densificar W.",
      "El presupuesto de 15 ms incluye retina, sparse mm, LIF, política y WebSocket.",
      "Docker multi-arquitectura elimina el clásico 'en mi máquina funciona'.",
      "Metal se usa para Gemma; el conectoma usa CPU NEON porque MPS no soporta COO disperso.",
    ],
    refs: [
      "Apple Inc. Metal Performance Shaders documentation.",
      "PyTorch Foundation. Sparse tensor operations and COO format.",
      "Docker Inc. Multi-platform builds for linux/arm64.",
      "Wydmuch et al. (2019). ViZDoom platform. IEEE T-CIAIG.",
    ],
  },
];

export const SLIDE_ICONS = { Eye, Activity, Award, Cpu, Layers, Sparkles, Radio };
