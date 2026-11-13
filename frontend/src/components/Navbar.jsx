import React from "react";
import {
  BrainCircuit,
  Brain,
  Presentation,
  Activity,
  Wifi,
  WifiOff,
  Power,
  Play,
  Save,
} from "lucide-react";

export default function Navbar({ mode, setMode, connected, telemetry, onSystemControl }) {
  const systemRunning = telemetry?.system_running ?? true;

  return (
    <header className="border-b border-[#383838] bg-[#252525] px-6 py-3 flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <div
          className="p-2 rounded-xl border border-[#4285f4]/45 text-[#448cff]"
          style={{ backgroundColor: "rgba(66, 133, 244, 0.15)" }}
        >
          <BrainCircuit className="w-6 h-6" />
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-tight text-[#ffffff] flex items-center gap-2">
            NEURODOOM OS
            <span
              className="text-xs font-mono px-2 py-0.5 rounded border border-[#4285f4]/45 text-[#448cff]"
              style={{ backgroundColor: "rgba(66, 133, 244, 0.15)" }}
            >
              FlyWire v783 + Gemma 3
            </span>
          </h1>
          <p className="text-xs text-[#c1c1c1]">
            Conectoma Biológico de Drosophila melanogaster en Tiempo Real (ARM64)
          </p>
        </div>
      </div>

      <div className="flex items-center gap-1.5 bg-[#181818] p-1 rounded-xl border border-[#383838]">
        <button
          onClick={() => setMode("conference")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition ${
            mode === "conference"
              ? "bg-[#4285f4] text-[#ffffff] border border-[#448cff]"
              : "text-[#c1c1c1] hover:text-[#ffffff] hover:bg-[#252525]"
          }`}
        >
          <Presentation className="w-4 h-4" />
          1. Explicación Interactiva (5 Etapas)
        </button>
        <button
          onClick={() => setMode("arena")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition ${
            mode === "arena"
              ? "bg-[#4285f4] text-[#ffffff] border border-[#448cff]"
              : "text-[#c1c1c1] hover:text-[#ffffff] hover:bg-[#252525]"
          }`}
        >
          <Activity className="w-4 h-4" />
          2. Laboratorio en Vivo (Mission Control)
        </button>
        <button
          onClick={() => setMode("connectome")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition ${
            mode === "connectome"
              ? "bg-[#4285f4] text-[#ffffff] border border-[#448cff]"
              : "text-[#c1c1c1] hover:text-[#ffffff] hover:bg-[#252525]"
          }`}
        >
          <Brain className="w-4 h-4" />
          3. Conectoma 3D
        </button>
      </div>

      <div className="flex items-center gap-3 text-xs font-mono">
        {telemetry && (
          <div className="hidden md:flex items-center gap-3 text-[#c1c1c1]">
            <span>
              SPK/STEP: <strong className="text-[#ea4335]">{telemetry.biophysics.total_spikes}</strong>
            </span>
            <span>
              FPS: <strong className="text-[#448cff]">{telemetry.actual_fps ?? telemetry.target_fps ?? 30}</strong>
            </span>
            <span>
              LATENCIA: <strong className="text-[#fbbc05]">{telemetry.biophysics.latency_ms} ms</strong>
            </span>
            <span>
              DOPAMINA: <strong className="text-[#34a853]">{telemetry.biophysics.dopamine_level}</strong>
            </span>
            <span>
              BAJAS: <strong className="text-[#ea4335]">{telemetry.total_kills ?? 0}</strong>
            </span>
          </div>
        )}
        <button
          onClick={() => onSystemControl?.({ running: !systemRunning, save: true })}
          title={
            systemRunning
              ? "Detiene la simulación y guarda en disco todo el aprendizaje y las bajas acumuladas"
              : "Reanuda el sistema con todo el aprendizaje y bajas guardadas"
          }
          style={{
            backgroundColor: systemRunning
              ? "rgba(251, 188, 5, 0.15)"
              : "rgba(52, 168, 83, 0.15)",
          }}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border font-semibold transition ${
            systemRunning
              ? "border-[#fbbc05]/60 text-[#fbbc05] hover:border-[#fbbc05]"
              : "border-[#34a853] text-[#34a853] hover:bg-[#34a853] hover:text-[#ffffff]"
          }`}
        >
          {systemRunning ? (
            <>
              <Power className="w-3.5 h-3.5" />
              Parar y Guardar
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5" />
              Iniciar Sistema
            </>
          )}
        </button>
        <span
          style={{
            backgroundColor: !connected
              ? "rgba(234, 67, 53, 0.15)"
              : systemRunning
              ? "rgba(52, 168, 83, 0.15)"
              : "rgba(251, 188, 5, 0.15)",
          }}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full border ${
            !connected
              ? "border-[#ea4335]/50 text-[#ea4335]"
              : systemRunning
              ? "border-[#34a853]/50 text-[#34a853]"
              : "border-[#fbbc05]/50 text-[#fbbc05]"
          }`}
        >
          {!connected ? (
            <WifiOff className="w-3.5 h-3.5" />
          ) : systemRunning ? (
            <Wifi className="w-3.5 h-3.5" />
          ) : (
            <Save className="w-3.5 h-3.5" />
          )}
          {!connected
            ? "RECONECTANDO..."
            : systemRunning
            ? "STREAM 35Hz ONLINE"
            : `PAUSA · ${telemetry?.total_kills ?? 0} BAJAS GUARDADAS`}
        </span>
      </div>
    </header>
  );
}
