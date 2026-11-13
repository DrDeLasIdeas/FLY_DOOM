import React, { useEffect, useRef, useState } from "react";
import { Maximize2, Minimize2 } from "lucide-react";
import Connectome3D from "./Connectome3D.jsx";
import SpikeOscilloscope from "./SpikeOscilloscope.jsx";
import GemmaBrainConsole from "./GemmaBrainConsole.jsx";
import MotorDecision from "./MotorDecision.jsx";
import TrainingPanel from "./TrainingPanel.jsx";

export default function LiveArena({
  telemetry,
  history,
  onDopaminePulse,
  onModulate,
  onTraining,
  onSystemControl,
  onSwitchScenario,
  onUpdateSpeed,
  onResetEpisode,
  onOpenStudio,
}) {
  const killRef = useRef(null);
  const doomBoxRef = useRef(null);
  const [killFlash, setKillFlash] = useState(false);
  const [doomExpanded, setDoomExpanded] = useState(false);

  const toggleDoomFullscreen = async () => {
    const next = !doomExpanded;
    setDoomExpanded(next);
    try {
      if (next && doomBoxRef.current?.requestFullscreen && !document.fullscreenElement) {
        await doomBoxRef.current.requestFullscreen();
      } else if (!next && document.fullscreenElement) {
        await document.exitFullscreen?.();
      }
    } catch {
      // fallback to fixed full-viewport overlay in the same tab
    }
  };

  useEffect(() => {
    const onFullscreenChange = () => {
      if (!document.fullscreenElement && doomExpanded) {
        setDoomExpanded(false);
      }
    };
    const onKeyDown = (event) => {
      if (event.key === "Escape" && doomExpanded) {
        setDoomExpanded(false);
      }
    };
    document.addEventListener("fullscreenchange", onFullscreenChange);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("fullscreenchange", onFullscreenChange);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [doomExpanded]);

  useEffect(() => {
    const total = telemetry?.total_kills ?? 0;
    if (killRef.current === null) {
      killRef.current = total;
      return undefined;
    }
    if (total > killRef.current) {
      killRef.current = total;
      setKillFlash(true);
      const timer = setTimeout(() => setKillFlash(false), 1400);
      return () => clearTimeout(timer);
    }
    killRef.current = total;
    return undefined;
  }, [telemetry?.total_kills]);

  if (!telemetry) {
    return (
      <div className="p-12 text-center font-mono text-slate-400">
        Sincronizando stream neuronal con neurodoom-core (ws://localhost:8000/ws/telemetry)...
      </div>
    );
  }

  const { rates, biophysics } = telemetry;

  return (
    <div className="max-w-[1600px] mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Columna Izquierda: Stream ViZDoom + Retina 64x64 + Neuronas Descendentes */}
      <div className="lg:col-span-4 space-y-4">
        <div
          ref={doomBoxRef}
          className={
            doomExpanded
              ? "fixed inset-0 z-50 bg-[#181818] p-4 sm:p-6 flex flex-col justify-between"
              : "bg-[#252525] border border-[#383838] rounded-xl p-4 space-y-3"
          }
        >
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
            <span className="text-[#448cff] uppercase font-semibold">
              {telemetry.scenario?.name || "Buffer Visual DOOM"} ({telemetry.arena_mode})
            </span>
            <div className="flex items-center gap-2">
              <span className="text-[#34a853]">
                EP #{telemetry.episode} | {telemetry.actual_fps ?? telemetry.target_fps ?? 30} FPS | REW: {telemetry.episode_reward}
              </span>
              <button
                type="button"
                onClick={toggleDoomFullscreen}
                style={{
                  backgroundColor: doomExpanded
                    ? "rgba(234, 67, 53, 0.15)"
                    : "rgba(66, 133, 244, 0.15)",
                }}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-mono uppercase tracking-wide transition ${
                  doomExpanded
                    ? "border-[#ea4335]/60 text-[#ea4335]"
                    : "border-[#4285f4]/60 text-[#448cff]"
                }`}
                title={
                  doomExpanded
                    ? "Salir de pantalla completa (Esc)"
                    : "Ampliar solo el Buffer Visual DOOM en pantalla completa"
                }
              >
                {doomExpanded ? (
                  <>
                    <Minimize2 className="w-3.5 h-3.5" />
                    Salir
                  </>
                ) : (
                  <>
                    <Maximize2 className="w-3.5 h-3.5" />
                    Ampliar
                  </>
                )}
              </button>
            </div>
          </div>
          <div
            className={
              doomExpanded
                ? "relative flex-1 min-h-0 flex items-center justify-center my-2 bg-[#181818] rounded-xl border border-[#383838]"
                : "relative bg-[#181818] rounded-xl"
            }
          >
            <img
              src={`data:image/jpeg;base64,${telemetry.frame_b64}`}
              alt="ViZDoom Live Stream"
              style={doomExpanded ? { imageRendering: "pixelated" } : undefined}
              className={`${
                doomExpanded
                  ? "w-full h-full max-h-[calc(100vh-90px)] object-contain"
                  : "w-full"
              } rounded-xl border transition-shadow ${
                (telemetry.policy?.attack_power ?? 0) > 0.5
                  ? "border-[#ea4335]"
                  : "border-[#383838]"
              }`}
            />
            {killFlash && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="px-4 py-2 rounded-xl bg-[#ea4335] text-[#ffffff] font-bold text-base tracking-wide shadow-2xl animate-pulse">
                  ¡MONSTRUO ELIMINADO!
                </div>
              </div>
            )}
            <div
              className={`absolute inset-0 pointer-events-none p-3 flex flex-col justify-between font-mono ${
                doomExpanded ? "text-xs sm:text-sm p-5" : "text-[10px]"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex gap-2">
                  <span className="px-2 py-0.5 rounded bg-[#181818]/90 border border-[#fbbc05]/50 text-[#fbbc05]">
                    AMMO {telemetry.ammo}/{telemetry.ammo_max ?? 26}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-[#181818]/90 border border-[#34a853]/50 text-[#34a853]">
                    VIDA {telemetry.health}
                  </span>
                </div>
                <span
                  style={{
                    backgroundColor: telemetry.enemy?.present
                      ? telemetry.enemy?.centered
                        ? "rgba(234, 67, 53, 0.22)"
                        : "rgba(251, 188, 5, 0.20)"
                      : "rgba(24, 24, 24, 0.85)",
                  }}
                  className={`px-2 py-0.5 rounded border font-semibold ${
                    telemetry.enemy?.present
                      ? telemetry.enemy?.centered
                        ? "border-[#ea4335] text-[#ea4335]"
                        : "border-[#fbbc05] text-[#fbbc05]"
                      : "border-[#383838] text-[#c1c1c1]"
                  }`}
                >
                  {telemetry.enemy?.present
                    ? telemetry.enemy?.centered
                      ? "🎯 EN FÓVEA"
                      : "HOSTIL DETECTADO"
                    : "SIN OBJETIVO"}
                </span>
              </div>
              <div className="flex items-end justify-between gap-2">
                <div className="flex gap-2">
                  <span className="px-2 py-0.5 rounded bg-[#181818]/90 border border-[#383838] text-[#ffffff]">
                    DISPAROS {telemetry.total_shots ?? 0}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-[#181818]/90 border border-[#ea4335]/50 text-[#ea4335]">
                    BAJAS {telemetry.total_kills ?? 0}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-[#181818]/90 border border-[#4285f4]/50 text-[#448cff]">
                    PRECISIÓN{" "}
                    {((telemetry.policy?.accuracy ?? telemetry.accuracy ?? 0) * 100).toFixed(1)}%
                  </span>
                </div>
                <span className="px-2 py-0.5 rounded bg-[#181818]/90 border border-[#34a853]/50 text-[#34a853]">
                  RECOMP. {(telemetry.shaped_reward ?? 0) >= 0 ? "+" : ""}
                  {telemetry.shaped_reward ?? 0}
                </span>
              </div>
            </div>
          </div>

          {!doomExpanded && (
          <div className="grid grid-cols-2 gap-3 pt-2">
            <div className="bg-[#181818] p-3 rounded-xl border border-[#383838] flex items-center gap-3">
              {telemetry.visual_buffer_b64 ? (
                <img
                  src={`data:image/jpeg;base64,${telemetry.visual_buffer_b64}`}
                  alt="FrameStack 4x84x84"
                  className="w-16 h-16 rounded border border-[#34a853]/60"
                  style={{ imageRendering: "pixelated" }}
                />
              ) : (
                <img
                  src={`data:image/jpeg;base64,${telemetry.retina_b64}`}
                  alt="Retina 64x64"
                  className="w-16 h-16 rounded border border-[#4285f4]/50"
                  style={{ imageRendering: "pixelated" }}
                />
              )}
              <div className="text-[11px] font-mono text-[#c1c1c1] space-y-1">
                <div className="text-[#34a853] font-bold">BUFFER CNN</div>
                <div className="text-[#ffffff]">
                  {(telemetry.visual_buffer_shape || [4, 84, 84]).join("×")}
                </div>
                <div>Gray + Norm [0,1]</div>
              </div>
            </div>

            <div className="bg-[#181818] p-3 rounded-xl border border-[#383838] flex items-center gap-3">
              <img
                src={`data:image/jpeg;base64,${telemetry.retina_b64}`}
                alt="Retina 64x64"
                className="w-16 h-16 rounded border border-[#4285f4]/50"
                style={{ imageRendering: "pixelated" }}
              />
              <div className="text-[11px] font-mono text-[#c1c1c1] space-y-1">
                <div className="text-[#448cff] font-bold">RETINA SNN 64×64</div>
                <div className="text-[#ffffff] truncate max-w-[120px]">{telemetry.action_name}</div>
                <div className="text-[#fbbc05]">DA: {biophysics.dopamine_level}</div>
              </div>
            </div>
          </div>
          )}
        </div>

        <div className="bg-[#252525] border border-[#383838] rounded-xl p-4 space-y-2.5 font-mono text-xs">
          <div className="text-[#448cff] uppercase">
            Decodificación Competitiva de Neuronas Descendentes
          </div>
          <div>
            <div className="flex justify-between">
              <span className="text-[#c1c1c1]">DNp20_L (Giro Izquierdo)</span>
              <span className="text-[#448cff] font-semibold">{rates.dn_left}</span>
            </div>
            <div className="w-full h-2 bg-[#181818] border border-[#383838] rounded overflow-hidden">
              <div
                className="h-full bg-[#4285f4]"
                style={{ width: `${Math.min(100, rates.dn_left * 500)}%` }}
              />
            </div>
          </div>
          <div>
            <div className="flex justify-between">
              <span className="text-[#c1c1c1]">DNp20_R (Giro Derecho)</span>
              <span className="text-[#fbbc05] font-semibold">{rates.dn_right}</span>
            </div>
            <div className="w-full h-2 bg-[#181818] border border-[#383838] rounded overflow-hidden">
              <div
                className="h-full bg-[#fbbc05]"
                style={{ width: `${Math.min(100, rates.dn_right * 500)}%` }}
              />
            </div>
          </div>
          <div>
            <div className="flex justify-between">
              <span className="text-[#c1c1c1]">DNpe017 (Carrera Frontal)</span>
              <span className="text-[#34a853] font-semibold">{rates.dn_move}</span>
            </div>
            <div className="w-full h-2 bg-[#181818] border border-[#383838] rounded overflow-hidden">
              <div
                className="h-full bg-[#34a853]"
                style={{ width: `${Math.min(100, (rates.dn_move ?? 0) * 500)}%` }}
              />
            </div>
          </div>
          <div>
            <div className="flex justify-between">
              <span className="text-[#c1c1c1]">DNp09 (Shotgun Trigger / Ataque)</span>
              <span className="text-[#ea4335] font-semibold">{rates.dn_attack}</span>
            </div>
            <div className="w-full h-2 bg-[#181818] border border-[#383838] rounded overflow-hidden">
              <div
                className="h-full bg-[#ea4335]"
                style={{ width: `${Math.min(100, rates.dn_attack * 500)}%` }}
              />
            </div>
          </div>
          <div className="pt-1.5 border-t border-[#383838]">
            <div className="flex justify-between text-[10px] text-[#c1c1c1]">
              <span>POTENCIA DE ATAQUE (DNp09)</span>
              <span className="text-[#ea4335] font-semibold">
                {(((telemetry.policy?.attack_power ?? 0) * 100)).toFixed(1)}%
              </span>
            </div>
            <div className="w-full h-2 bg-[#181818] border border-[#383838] rounded overflow-hidden">
              <div
                className="h-full bg-[#ea4335]"
                style={{ width: `${Math.min(100, (telemetry.policy?.attack_power ?? 0) * 100)}%` }}
              />
            </div>
          </div>
        </div>

        <MotorDecision policy={telemetry.policy} />
      </div>

      {/* Columna Central: Conectoma 3D + Osciloscopio */}
      <div className="lg:col-span-5 space-y-4">
        <Connectome3D
          connectome={telemetry.connectome}
          neurons3d={telemetry.neurons_3d}
          attackPower={telemetry.policy?.attack_power ?? 0}
          onOpenStudio={onOpenStudio}
        />
        <SpikeOscilloscope rates={rates} history={history} />
      </div>

      {/* Columna Derecha: Consola Gemma 3 + Intervención Manual */}
      <div className="lg:col-span-3 space-y-4">
        <GemmaBrainConsole
          gemma={telemetry.gemma}
          biophysics={biophysics}
          onDopaminePulse={onDopaminePulse}
          onModulate={onModulate}
        />
        <TrainingPanel
          policy={telemetry.policy}
          scenario={telemetry.scenario}
          actualFps={telemetry.actual_fps}
          targetFps={telemetry.target_fps}
          ticSkip={telemetry.tic_skip}
          systemRunning={telemetry.system_running ?? true}
          onTraining={onTraining}
          onSystemControl={onSystemControl}
          onSwitchScenario={onSwitchScenario}
          onUpdateSpeed={onUpdateSpeed}
          onResetEpisode={onResetEpisode}
        />
      </div>
    </div>
  );
}
