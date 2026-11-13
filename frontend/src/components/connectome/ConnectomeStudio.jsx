import React, { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Brain,
  Crosshair,
  Layers,
  Maximize2,
  Pause,
  Play,
  RotateCcw,
  Scissors,
  SlidersHorizontal,
  Zap,
} from "lucide-react";
import ConnectomeScene from "./ConnectomeScene.jsx";
import ConnectomeFallback from "./ConnectomeFallback.jsx";
import NeuronInspector from "./NeuronInspector.jsx";
import RegionActivityList from "./RegionActivityList.jsx";
import { useTopology } from "./useTopology.js";
import { REGION_HEX, SYNAPSE_HEX, VOLTAGE_STOPS } from "./palette.js";

const PRESETS = [
  { key: "mosca", label: "Mosca" },
  { key: "frontal", label: "Frontal" },
  { key: "explotada", label: "Explotada" },
  { key: "sagital", label: "Sagital" },
];

const FILTERS = [
  { key: 0, label: "Todas" },
  { key: 1, label: "Excit." },
  { key: 2, label: "Inhib." },
  { key: 3, label: "Dopamina" },
];

const CLIP_AXES = [
  { key: "x", label: "Sagital X" },
  { key: "y", label: "Axial Y" },
  { key: "z", label: "Coronal Z" },
];

const SPEEDS = [0.1, 0.25, 0.5, 1];

function Section({ icon: Icon, title, right, children }) {
  return (
    <section className="bg-slate-900/90 border border-slate-800 rounded-xl p-3 space-y-2.5">
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider text-slate-400">
          <Icon className="w-3.5 h-3.5 text-cyan-400" />
          {title}
        </h3>
        {right}
      </div>
      {children}
    </section>
  );
}

function Toggle({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-2 py-1 rounded-md border text-[9px] font-mono uppercase tracking-wide transition ${
        active
          ? "border-cyan-500/70 bg-cyan-500/15 text-cyan-200"
          : "border-slate-700 text-slate-400 hover:border-slate-500"
      }`}
    >
      {children}
    </button>
  );
}

function format(value) {
  return Number(value ?? 0).toLocaleString("es-MX");
}

export default function ConnectomeStudio({ telemetry }) {
  const { topology, error } = useTopology();
  const [view, setView] = useState("mosca");
  const [filters, setFilters] = useState({ kind: 0, minWeight: 0 });
  const [clip, setClip] = useState({ enabled: false, axis: "x", value: 0.5 });
  const [paused, setPaused] = useState(false);
  const [timeScale, setTimeScale] = useState(1);
  const [explodeAmount, setExplodeAmount] = useState(null);
  const [hovered, setHovered] = useState(null);
  const [pinned, setPinned] = useState(null);

  const connectome = telemetry?.connectome;
  const attackPower = telemetry?.policy?.attack_power ?? 0;
  const regionActivity = connectome?.region_activity ?? {};
  const selected = pinned ?? hovered;

  const voltageGradient = useMemo(
    () =>
      `linear-gradient(90deg, ${VOLTAGE_STOPS.map(
        (stop) =>
          `rgb(${stop.color.map((c) => Math.round(c * 255)).join(",")}) ${stop.at * 100}%`,
      ).join(", ")})`,
    [],
  );

  const enterFullscreen = () => {
    try {
      document.documentElement.requestFullscreen?.();
    } catch (err) {
      console.warn("No se pudo activar pantalla completa:", err);
    }
  };

  useEffect(() => {
    const onKey = (event) => {
      const tag = event.target?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || event.target?.isContentEditable) return;
      if (event.code === "Space") {
        event.preventDefault();
        setPaused((previous) => !previous);
      }
      if (event.key === "r" || event.key === "R") {
        setView("mosca");
        setFilters({ kind: 0, minWeight: 0 });
        setClip({ enabled: false, axis: "x", value: 0.5 });
        setPaused(false);
        setTimeScale(1);
        setExplodeAmount(null);
        setPinned(null);
      }
      if (event.key === "1") {
        setView("mosca");
        setExplodeAmount(null);
      }
      if (event.key === "2") {
        setView("frontal");
        setExplodeAmount(null);
      }
      if (event.key === "3") {
        setView("explotada");
        setExplodeAmount(1.2);
      }
      if (event.key === "4") {
        setView("sagital");
        setExplodeAmount(null);
        setClip((previous) => ({ ...previous, enabled: true, axis: "x" }));
      }
      if (event.key === "c" || event.key === "C") {
        setClip((previous) => ({ ...previous, enabled: !previous.enabled }));
      }
      if (event.key === "f" || event.key === "F") {
        event.preventDefault();
        enterFullscreen();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const selectPreset = (key) => {
    setView(key);
    setExplodeAmount(key === "explotada" ? 1.2 : null);
    if (key === "sagital") {
      setClip((previous) => ({ ...previous, enabled: true, axis: "x" }));
    }
  };

  const reset = () => {
    setView("mosca");
    setFilters({ kind: 0, minWeight: 0 });
    setClip({ enabled: false, axis: "x", value: 0.5 });
    setPaused(false);
    setTimeScale(1);
    setExplodeAmount(null);
    setPinned(null);
  };

  const stats = topology?.synapseStats ?? {};
  const biophysics = topology?.biophysics ?? {};

  return (
    <div className="h-[calc(100vh-77px)] min-h-[620px] p-3 grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_360px] gap-3">
      <div className="relative rounded-2xl border border-slate-800 bg-slate-950 overflow-hidden min-h-[440px]">
        {topology ? (
          <ConnectomeScene
            topology={topology}
            connectome={connectome}
            attackPower={attackPower}
            view={view}
            filters={filters}
            clip={clip}
            paused={paused}
            timeScale={timeScale}
            explodeAmount={explodeAmount}
            selectedIndex={pinned?.index ?? null}
            onHover={setHovered}
            onSelect={setPinned}
          />
        ) : (
          <ConnectomeFallback
            neurons3d={telemetry?.neurons_3d}
            attackPower={attackPower}
            error={error}
          />
        )}

        <div className="absolute top-3 left-3 pointer-events-none">
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-300">
              <Brain className="w-4 h-4" />
            </span>
            <div>
              <div className="text-[11px] font-bold tracking-[0.18em] text-cyan-300">
                CONECTOMA 3D · FLYWIRE v783
              </div>
              <div className="text-[9px] font-mono text-slate-400">
                {topology
                  ? `${format(topology.numNeurons)} neuronas · ${format(topology.numVisible)} dinámicas · ${format(topology.numGhost)} ghost`
                  : "cargando topología anatómica..."}
              </div>
            </div>
          </div>
        </div>

        <div className="absolute top-3 right-3 flex flex-col items-end gap-2">
          <div className="flex gap-1">
            {PRESETS.map((preset) => (
              <button
                key={preset.key}
                onClick={() => selectPreset(preset.key)}
                className={`px-2 py-1 rounded-md border text-[9px] font-mono uppercase tracking-wide transition ${
                  view === preset.key
                    ? "border-cyan-500/70 bg-cyan-500/15 text-cyan-200"
                    : "border-slate-700 bg-slate-950/70 text-slate-400 hover:border-slate-500"
                }`}
              >
                {preset.label}
              </button>
            ))}
            <button
              onClick={enterFullscreen}
              className="p-1.5 rounded-md border border-slate-700 bg-slate-950/70 text-slate-400 hover:text-cyan-300 hover:border-cyan-500/50"
              title="Pantalla completa (F)"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-md border border-slate-800 bg-slate-950/80 font-mono text-[9px]">
            <span
              className={`inline-block w-1.5 h-1.5 rounded-full ${
                telemetry ? "bg-emerald-400 animate-pulse" : "bg-rose-400"
              }`}
            />
            <span className={telemetry ? "text-emerald-300" : "text-rose-300"}>
              {telemetry ? "STREAM ONLINE" : "SIN STREAM"}
            </span>
            <span className="text-slate-600">|</span>
            <span className="text-slate-400">SEQ {connectome?.seq ?? 0}</span>
          </div>
        </div>

        <div className="absolute bottom-3 left-3 rounded-lg border border-slate-800 bg-slate-950/85 px-3 py-2 space-y-1.5 pointer-events-none">
          <div className="text-[8px] font-mono uppercase tracking-wider text-slate-500">
            Potencial de membrana
          </div>
          <div className="h-1.5 w-44 rounded-full" style={{ background: voltageGradient }} />
          <div className="flex justify-between font-mono text-[8px] text-slate-500">
            <span>V_rest {biophysics.v_rest ?? -52} mV</span>
            <span>V_th {biophysics.v_thresh ?? -45} mV</span>
          </div>
          <div className="flex flex-wrap gap-x-3 gap-y-0.5 font-mono text-[8px] text-slate-400">
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: SYNAPSE_HEX.excitatory }} />
              excitatoria
            </span>
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: SYNAPSE_HEX.inhibitory }} />
              inhibitoria
            </span>
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: SYNAPSE_HEX.dopamine }} />
              dopamina
            </span>
          </div>
          <div className="font-mono text-[8px] text-slate-600">
            arrastra para orbitar · scroll para zoom
          </div>
        </div>

        <div className="absolute bottom-3 right-3 rounded-lg border border-slate-800 bg-slate-950/85 px-3 py-2 font-mono text-[9px] text-slate-400 pointer-events-none">
          <div className="flex items-center gap-3">
            <span>
              SPK/STEP <strong className="text-cyan-300">{format(connectome?.spike_count ?? 0)}</strong>
            </span>
            <span>
              LAT <strong className="text-emerald-300">{telemetry?.biophysics?.latency_ms ?? 0} ms</strong>
            </span>
            <span>
              V̄ <strong className="text-amber-300">{connectome?.mean_v ?? 0}</strong>
            </span>
          </div>
        </div>
      </div>

      <aside className="min-h-0 overflow-y-auto space-y-3 pr-1">
        <Section
          icon={SlidersHorizontal}
          title="Sinapsis"
          right={
            <span className="font-mono text-[9px] text-slate-500">
              {format(topology?.edges?.length ? topology.edges.length / 2 : 0)} visibles
            </span>
          }
        >
          <div className="grid grid-cols-4 gap-1">
            {FILTERS.map((filter) => (
              <Toggle
                key={filter.key}
                active={filters.kind === filter.key}
                onClick={() => setFilters((previous) => ({ ...previous, kind: filter.key }))}
              >
                {filter.label}
              </Toggle>
            ))}
          </div>
          <label className="block text-[9px] font-mono text-slate-400">
            Peso mínimo <strong className="text-slate-200">{filters.minWeight.toFixed(2)}</strong>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={filters.minWeight}
              onChange={(event) =>
                setFilters((previous) => ({ ...previous, minWeight: Number(event.target.value) }))
              }
              className="w-full accent-cyan-400 mt-1"
            />
          </label>
        </Section>

        <Section
          icon={Scissors}
          title="Corte y sección"
          right={
            <Toggle
              active={clip.enabled}
              onClick={() => setClip((previous) => ({ ...previous, enabled: !previous.enabled }))}
            >
              {clip.enabled ? "ON" : "OFF"}
            </Toggle>
          }
        >
          <div className="grid grid-cols-3 gap-1">
            {CLIP_AXES.map((axis) => (
              <Toggle
                key={axis.key}
                active={clip.axis === axis.key}
                onClick={() => setClip((previous) => ({ ...previous, axis: axis.key, enabled: true }))}
              >
                {axis.label}
              </Toggle>
            ))}
          </div>
          <label className="block text-[9px] font-mono text-slate-400">
            Plano de corte <strong className="text-slate-200">{(clip.value * 100).toFixed(0)}%</strong>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={clip.value}
              onChange={(event) =>
                setClip((previous) => ({ ...previous, value: Number(event.target.value) }))
              }
              className="w-full accent-cyan-400 mt-1"
            />
          </label>
        </Section>

        <Section
          icon={Activity}
          title="Tiempo y animación"
          right={
            <span className="font-mono text-[9px] text-cyan-300">
              {paused ? "PARADO" : `${timeScale.toFixed(2).replace(/\.00$/, "")}×`}
            </span>
          }
        >
          <div className="flex flex-wrap items-center gap-1">
            <button
              type="button"
              onClick={() => setPaused((previous) => !previous)}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md border text-[9px] font-mono uppercase transition ${
                paused
                  ? "border-amber-500/70 bg-amber-500/20 text-amber-200"
                  : "border-rose-500/50 bg-rose-500/10 text-rose-200 hover:bg-rose-500/20"
              }`}
            >
              {paused ? <Play className="w-3 h-3" /> : <Pause className="w-3 h-3" />}
              {paused ? "Reanudar" : "Parar"}
            </button>
            {SPEEDS.map((speed) => (
              <Toggle
                key={speed}
                active={!paused && Math.abs(timeScale - speed) < 0.02}
                onClick={() => {
                  setTimeScale(speed);
                  setPaused(false);
                }}
              >
                {speed}×
              </Toggle>
            ))}
            <button
              type="button"
              onClick={reset}
              className="ml-auto p-1.5 rounded-md border border-slate-700 text-slate-400 hover:text-rose-300 hover:border-rose-500/50"
              title="Reiniciar vista y filtros (R)"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
          <label className="block text-[9px] font-mono text-slate-400">
            Velocidad de animación{" "}
            <strong className="text-slate-200">{(timeScale * 100).toFixed(0)}%</strong>
            <input
              type="range"
              min="0.05"
              max="1.5"
              step="0.05"
              value={timeScale}
              onChange={(event) => {
                setTimeScale(Number(event.target.value));
                setPaused(false);
              }}
              className="w-full accent-cyan-400 mt-1"
            />
          </label>
          <label className="block text-[9px] font-mono text-slate-400">
            Separar regiones{" "}
            <strong className="text-slate-200">
              {Math.round(((explodeAmount ?? (view === "explotada" ? 1.2 : 0)) / 1.5) * 100)}%
            </strong>
            <input
              type="range"
              min="0"
              max="1.5"
              step="0.05"
              value={explodeAmount ?? (view === "explotada" ? 1.2 : 0)}
              onChange={(event) => setExplodeAmount(Number(event.target.value))}
              className="w-full accent-violet-400 mt-1"
            />
          </label>
          <div className="font-mono text-[9px] text-slate-500">
            Espacio parar · 1–4 presets · C corte · F pantalla completa
          </div>
        </Section>

        <Section icon={Crosshair} title="Neurona inspeccionada">
          <NeuronInspector
            info={selected}
            pinned={Boolean(pinned)}
            onClear={() => setPinned(null)}
          />
        </Section>

        <Section icon={Layers} title="Actividad por región" right={<span className="font-mono text-[9px] text-slate-500">tasa media/step</span>}>
          {topology ? (
            <RegionActivityList
              names={topology.regionNames}
              activity={regionActivity}
            />
          ) : (
            <div className="text-[10px] font-mono text-slate-500">sin topología</div>
          )}
        </Section>

        <Section icon={Zap} title="Ficha técnica">
          <div className="grid grid-cols-2 gap-x-3 gap-y-1 font-mono text-[9px]">
            <span className="text-slate-500">Sinapsis totales</span>
            <span className="text-slate-200">{format(stats.num_synapses)}</span>
            <span className="text-slate-500">Densidad</span>
            <span className="text-slate-200">
              {stats.density != null ? `${(stats.density * 100).toFixed(3)}%` : "—"}
            </span>
            <span className="text-slate-500">Excitatorias</span>
            <span className="text-cyan-300">{format(stats.excitatory)}</span>
            <span className="text-slate-500">Inhibitorias</span>
            <span className="text-fuchsia-300">{format(stats.inhibitory)}</span>
            <span className="text-slate-500">Regiones</span>
            <span className="text-slate-200">{topology?.regionNames?.length ?? 0}</span>
            <span className="text-slate-500">Mallas</span>
            <span className="text-slate-200">{topology?.meshes?.length ?? 0}</span>
            <span className="text-slate-500">Sub-pasos</span>
            <span className="text-slate-200">{biophysics.substeps_per_frame ?? biophysics.substeps ?? 4}</span>
            <span className="text-slate-500">Dispositivo</span>
            <span className="text-emerald-300">{biophysics.device ?? "cpu"}</span>
          </div>
          <div className="pt-1 border-t border-slate-800 font-mono text-[8px] text-slate-600">
            W dispersa COO · nunca densificada · R-STDP con dopamina PAM/PPL1
          </div>
        </Section>

        <div className="flex flex-wrap gap-x-2 gap-y-1 px-1 font-mono text-[8px] text-slate-600">
          {topology?.regionNames?.map((name, index) => (
            <span key={name} className="flex items-center gap-1">
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ backgroundColor: REGION_HEX[index] ?? "#64748b" }}
              />
              {name}
            </span>
          ))}
        </div>
      </aside>
    </div>
  );
}
