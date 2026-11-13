import React, { useEffect } from "react";
import {
  Crosshair,
  Maximize2,
  Music,
  Pause,
  Play,
  Power,
  RotateCcw,
  Skull,
  Target,
  Volume2,
  VolumeX,
  X,
} from "lucide-react";
import LineChart from "./charts/LineChart.jsx";
import BarChart from "./charts/BarChart.jsx";
import ActionBars from "./charts/ActionBars.jsx";
import Sparkline from "./charts/Sparkline.jsx";
import KillFeed from "./charts/KillFeed.jsx";
import ConnectomePanel from "./connectome/ConnectomePanel.jsx";
import { useKillFeed } from "../hooks/useKillFeed.js";

const DN_BARS = [
  { key: "dn_left", label: "DNp20_L", color: "bg-cyan-400" },
  { key: "dn_right", label: "DNp20_R", color: "bg-sky-400" },
  { key: "dn_attack", label: "DNp09", color: "bg-rose-500" },
  { key: "dn_move", label: "DNp_move", color: "bg-fuchsia-400" },
];

function Kpi({ label, value, tone = "text-white" }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg px-2 py-1.5">
      <div className="text-[9px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className={`text-sm font-bold ${tone}`}>{value}</div>
    </div>
  );
}

function Card({ title, right, children }) {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wider text-slate-400">{title}</span>
        {right && <span className="text-[10px] font-mono text-slate-500">{right}</span>}
      </div>
      {children}
    </div>
  );
}

export default function FullscreenArena({
  telemetry,
  history = [],
  onTraining,
  onSystemControl,
  onSwitchScenario,
  audioEnabled = false,
  musicEnabled = true,
  sfxEnabled = true,
  onToggleAudio,
  onToggleMusic,
  onToggleSfx,
  onExit,
  onRequestBrowserFullscreen,
}) {
  const isMusicActive = audioEnabled && musicEnabled;
  const isSfxActive = audioEnabled && sfxEnabled;
  const scenarios = telemetry?.scenario?.available_scenarios || [];
  const { events, flash } = useKillFeed(telemetry);
  const policy = telemetry?.policy;
  const rates = telemetry?.rates ?? {};
  const systemRunning = telemetry?.system_running ?? true;

  useEffect(() => {
    const onKey = (event) => {
      const tag = event.target?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (event.code === "Space") {
        event.preventDefault();
        onTraining?.({ enabled: !policy?.training_enabled });
      }
      if (event.key === "g" || event.key === "G") {
        onTraining?.({ greedy: !policy?.greedy });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onTraining, policy?.training_enabled, policy?.greedy]);

  if (!telemetry) {
    return (
      <div className="fixed inset-0 z-50 bg-slate-950 text-slate-100 flex flex-col items-center justify-center gap-4">
        <p className="font-mono text-slate-400">
          Sincronizando arena fullscreen con el stream neuronal...
        </p>
        <button
          onClick={onExit}
          className="px-4 py-2 rounded-lg border border-slate-700 hover:border-rose-500/60 text-sm"
        >
          Volver al laboratorio
        </button>
      </div>
    );
  }

  const historyData = policy?.history ?? [];
  const rewards = historyData.map((h) => Number(h.reward) || 0);
  const effectiveness = historyData.map((h) => (Number(h.accuracy) || 0) * 100);
  let running = 0;
  const killsSeries = historyData.map((h) => (running += Number(h.kills) || 0));
  const dnAttackSeries = history.map((r) => Number(r?.dn_attack) || 0);
  const attackPower = policy?.attack_power ?? 0;
  const accuracy = (policy?.accuracy ?? telemetry.accuracy ?? 0) * 100;

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-slate-950 text-slate-100">
      <header className="flex flex-wrap items-center justify-between gap-3 px-4 py-2 border-b border-slate-800 bg-slate-950/95">
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold tracking-[0.2em] text-cyan-400">
            NEURODOOM · {telemetry.scenario?.name?.toUpperCase() || "ARENA"}
          </span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-fuchsia-500/40 text-fuchsia-300">
            {telemetry.arena_mode} · {telemetry.actual_fps ?? 30} FPS
          </span>
          {scenarios.length > 0 && (
            <select
              value={telemetry.scenario?.id || "defend_the_center"}
              onChange={(e) => onSwitchScenario?.(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded px-2 py-0.5 text-[11px] font-mono text-cyan-200 focus:outline-none focus:border-cyan-400"
              title="Cambiar escenario de ViZDoom en caliente"
            >
              {scenarios.map((sc) => (
                <option key={sc.id} value={sc.id}>
                  {sc.name}
                </option>
              ))}
            </select>
          )}
          <span className="hidden sm:inline text-[10px] font-mono text-slate-400">
            EP #{telemetry.episode} · {telemetry.action_name}
          </span>
        </div>
        <div className="flex items-center gap-2 font-mono text-[11px]">
          <span className="px-2 py-1 rounded bg-slate-900 border border-amber-500/40 text-amber-300">
            AMMO {telemetry.ammo}/{telemetry.ammo_max ?? 26}
          </span>
          <span className="px-2 py-1 rounded bg-slate-900 border border-emerald-500/40 text-emerald-300">
            VIDA {telemetry.health}
          </span>
          <span className="px-2 py-1 rounded bg-slate-900 border border-rose-500/40 text-rose-300">
            BAJAS {telemetry.total_kills ?? 0}
          </span>
          <div className="flex items-center gap-1 bg-slate-900 p-0.5 rounded-lg border border-slate-800">
            <button
              onClick={onToggleAudio}
              title="Prender / Apagar todo el audio retro"
              className={`flex items-center gap-1 px-2 py-1 rounded font-bold transition ${
                audioEnabled
                  ? "bg-emerald-500/20 text-emerald-300"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {audioEnabled ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
              {audioEnabled ? "Audio" : "Mute"}
            </button>
            <button
              onClick={onToggleMusic}
              title="Prender / Apagar música retro"
              className={`flex items-center gap-1 px-2 py-1 rounded transition ${
                isMusicActive
                  ? "bg-cyan-500/20 text-cyan-300 font-bold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Music className="w-3.5 h-3.5" />
              Música {isMusicActive ? "ON" : "OFF"}
            </button>
            <button
              onClick={onToggleSfx}
              title="Prender / Apagar sonido de disparos"
              className={`flex items-center gap-1 px-2 py-1 rounded transition ${
                isSfxActive
                  ? "bg-rose-500/20 text-rose-300 font-bold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Crosshair className="w-3.5 h-3.5" />
              Disparos {isSfxActive ? "ON" : "OFF"}
            </button>
          </div>
          <button
            onClick={() => onSystemControl?.({ running: !systemRunning, save: true })}
            className={`flex items-center gap-1 px-2.5 py-1 rounded border font-bold transition ${
              systemRunning
                ? "bg-amber-500/15 border-amber-500/50 text-amber-200 hover:bg-amber-500/25"
                : "bg-emerald-500 text-slate-950 border-emerald-400 hover:bg-emerald-400"
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
          <button
            onClick={onRequestBrowserFullscreen}
            title="Pantalla completa del navegador"
            className="p-1.5 rounded bg-slate-900 border border-slate-700 hover:border-cyan-500/60"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
          <button
            onClick={onExit}
            title="Salir (Esc)"
            className="p-1.5 rounded bg-slate-900 border border-slate-700 hover:border-rose-500/60"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </header>

      <div className="flex-1 min-h-0 grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_390px] gap-3 p-3">
        <section
          className={`relative min-h-0 flex items-center justify-center rounded-2xl bg-black overflow-hidden border-2 transition-colors ${
            attackPower > 0.5 ? "border-rose-500/70" : "border-slate-800"
          }`}
        >
          <img
            src={`data:image/jpeg;base64,${telemetry.frame_b64}`}
            alt="ViZDoom fullscreen"
            className="max-h-full max-w-full object-contain"
            style={{ imageRendering: "pixelated" }}
          />

          {flash && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="px-6 py-3 rounded-xl bg-rose-500/90 text-white font-black text-2xl tracking-wide shadow-2xl animate-pulse">
                ¡MONSTRUO ELIMINADO!
              </div>
            </div>
          )}

          <div className="absolute inset-0 pointer-events-none p-3 flex flex-col justify-between font-mono text-[11px]">
            <div className="flex items-start justify-between gap-2">
              <div className="flex gap-2">
                <span className="px-2 py-0.5 rounded bg-slate-950/80 border border-amber-500/40 text-amber-300">
                  AMMO {telemetry.ammo}/{telemetry.ammo_max ?? 26}
                </span>
                <span className="px-2 py-0.5 rounded bg-slate-950/80 border border-emerald-500/40 text-emerald-300">
                  VIDA {telemetry.health}
                </span>
              </div>
              <span
                className={`px-2 py-0.5 rounded bg-slate-950/80 border ${
                  telemetry.enemy?.present
                    ? telemetry.enemy?.centered
                      ? "border-emerald-400 text-emerald-300"
                      : "border-amber-400 text-amber-300"
                    : "border-slate-600 text-slate-400"
                }`}
              >
                {telemetry.enemy?.present
                  ? telemetry.enemy?.centered
                    ? "TARGET LOCK"
                    : "HOSTILE"
                  : "SIN OBJETIVO"}
              </span>
            </div>
            <div className="flex items-end justify-between gap-2">
              <div className="flex flex-wrap gap-2">
                <span className="px-2 py-0.5 rounded bg-slate-950/80 border border-slate-700 text-slate-200">
                  DISPAROS {telemetry.total_shots ?? 0}
                </span>
                <span className="px-2 py-0.5 rounded bg-slate-950/80 border border-rose-500/40 text-rose-300">
                  BAJAS {telemetry.total_kills ?? 0}
                </span>
                <span className="px-2 py-0.5 rounded bg-slate-950/80 border border-cyan-500/40 text-cyan-300">
                  EFECTIVIDAD {accuracy.toFixed(1)}%
                </span>
              </div>
              <span className="px-2 py-0.5 rounded bg-slate-950/80 border border-fuchsia-500/40 text-fuchsia-300">
                RECOMP. {(telemetry.shaped_reward ?? 0) >= 0 ? "+" : ""}
                {telemetry.shaped_reward ?? 0}
              </span>
            </div>
          </div>

          <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none w-24">
            <div className="text-[9px] font-mono text-rose-300 mb-1">DNp09</div>
            <div className="h-24 w-2 bg-slate-950/80 rounded overflow-hidden flex flex-col justify-end border border-rose-500/40">
              <div
                className="w-full bg-gradient-to-t from-amber-400 to-rose-500 transition-all duration-75"
                style={{ height: `${Math.min(100, attackPower * 100)}%` }}
              />
            </div>
          </div>
        </section>

        <aside className="min-h-0 overflow-y-auto space-y-3 pr-1">
          <div className="grid grid-cols-3 gap-2 font-mono">
            <Kpi label="Episodios" value={policy?.episodes ?? 0} tone="text-cyan-300" />
            <Kpi label="Recomp. media" value={(policy?.avg_reward ?? 0).toFixed(2)} tone="text-rose-300" />
            <Kpi label="Mejor recomp." value={(policy?.best_reward ?? 0).toFixed(2)} tone="text-amber-300" />
            <Kpi label="Bajas" value={policy?.total_kills ?? 0} tone="text-rose-300" />
            <Kpi label="Disparos" value={policy?.total_shots ?? 0} tone="text-slate-200" />
            <Kpi label="Efectividad" value={`${accuracy.toFixed(1)}%`} tone="text-emerald-300" />
          </div>

          <Card
            title="Conectoma 3D en vivo"
            right={`${telemetry.connectome?.visible_count ?? 0} neuronas`}
          >
            <ConnectomePanel
              connectome={telemetry.connectome}
              neurons3d={telemetry.neurons_3d}
              attackPower={attackPower}
              compact
              bare
            />
          </Card>

          <Card
            title="Curva de recompensa"
            right={`${historyData.length} eps · pérdida ${policy?.last_loss ?? 0}`}
          >
            <LineChart values={rewards} color="#fb7185" height={72} />
          </Card>

          <Card title="Efectividad por episodio" right="bajas/disparo">
            <LineChart
              values={effectiveness}
              color="#34d399"
              height={64}
              min={0}
              max={Math.max(100, ...effectiveness)}
            />
          </Card>

          <Card title="Bajas acumuladas (ventana)" right={`mejor ${policy?.best_kills ?? 0}`}>
            <LineChart values={killsSeries} color="#f59e0b" height={56} />
          </Card>

          <Card
            title={`Decisión ${policy?.algorithm || "PPO-CNN"}`}
            right={
              policy?.greedy
                ? "GREEDY"
                : `EXPL. ${((policy?.exploration_rate ?? 0) * 100).toFixed(0)}%`
            }
          >
            <ActionBars
              probs={policy?.action_probs ?? []}
              labels={policy?.action_labels}
              actionIdx={policy?.action_idx ?? -1}
              compact
            />
            <div className="pt-1">
              <div className="flex justify-between text-[9px] font-mono text-slate-500">
                <span>POTENCIA DE ATAQUE</span>
                <span className="text-rose-300">{(attackPower * 100).toFixed(1)}%</span>
              </div>
              <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-amber-400 to-rose-500"
                  style={{ width: `${Math.min(100, attackPower * 100)}%` }}
                />
              </div>
            </div>
          </Card>

          <Card title="Neuronas descendentes" right="tasas en vivo">
            <BarChart
              items={DN_BARS.map((b) => ({
                label: b.label,
                value: rates[b.key] ?? 0,
                color: b.color,
              }))}
              scale={1}
            />
            <div className="pt-1">
              <div className="flex justify-between text-[9px] font-mono text-slate-500 mb-0.5">
                <span>DNp09 (ventana)</span>
                <span>{((rates.dn_attack ?? 0) * 100).toFixed(1)}%</span>
              </div>
              <Sparkline values={dnAttackSeries} color="#fb7185" height={30} />
            </div>
          </Card>

          <Card title="Registro de bajas" right={`${events.length} recientes`}>
            <KillFeed events={events} />
          </Card>

          <div className="grid grid-cols-3 gap-2 font-mono text-[10px]">
            <button
              onClick={() => onTraining?.({ enabled: !policy?.training_enabled })}
              className="flex items-center justify-center gap-1 px-2 py-2 rounded-lg bg-slate-900 border border-slate-700 hover:border-emerald-500/60"
            >
              {policy?.training_enabled ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              {policy?.training_enabled ? "Pausar" : "Entrenar"}
            </button>
            <button
              onClick={() => onTraining?.({ greedy: !policy?.greedy })}
              className="flex items-center justify-center gap-1 px-2 py-2 rounded-lg bg-slate-900 border border-slate-700 hover:border-cyan-500/60"
            >
              <Target className="w-3.5 h-3.5" />
              {policy?.greedy ? "Explorar" : "Evaluar"}
            </button>
            <button
              onClick={() => onTraining?.({ reset: true })}
              className="flex items-center justify-center gap-1 px-2 py-2 rounded-lg bg-slate-900 border border-slate-700 hover:border-rose-500/60"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reiniciar
            </button>
          </div>

          <div className="flex items-center justify-between text-[9px] font-mono text-slate-500 px-1">
            <span className="flex items-center gap-1">
              <Crosshair className="w-3 h-3" /> {telemetry.action_name}
            </span>
            <span className="flex items-center gap-1">
              <Skull className="w-3 h-3" /> 100% local · F/Esc · Space · G
            </span>
          </div>
        </aside>
      </div>
    </div>
  );
}
