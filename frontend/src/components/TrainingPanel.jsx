import React from "react";
import {
  Activity,
  Crosshair,
  Gauge,
  Layers,
  Pause,
  Play,
  Power,
  RefreshCw,
  RotateCcw,
  Save,
  Skull,
  Target,
} from "lucide-react";

function MiniSeriesChart({ values = [], stroke = "#34a853", fill = "rgba(52, 168, 83, 0.15)", emptyText }) {
  if (values.length < 2) {
    return (
      <div className="h-16 flex items-center justify-center text-[10px] text-[#c1c1c1] font-mono bg-[#181818] border border-dashed border-[#383838] rounded-lg">
        {emptyText}
      </div>
    );
  }

  const w = 260;
  const h = 64;
  const pad = 5;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pts = values
    .map((v, i) => {
      const x = pad + (i / (values.length - 1)) * (w - pad * 2);
      const y = h - pad - ((v - min) / span) * (h - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <div className="relative bg-[#181818] border border-[#383838] rounded-lg p-1">
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-16">
        <polyline
          points={`${pad},${h - pad} ${pts} ${w - pad},${h - pad}`}
          fill={fill}
          stroke="none"
        />
        <polyline points={pts} fill="none" stroke={stroke} strokeWidth="1.8" />
      </svg>
      <div className="absolute top-1 right-2 text-[9px] font-mono" style={{ color: stroke }}>
        {max.toFixed(2)}
      </div>
      <div className="absolute bottom-1 right-2 text-[9px] font-mono text-[#c1c1c1]">
        {min.toFixed(2)}
      </div>
    </div>
  );
}

export default function TrainingPanel({
  policy,
  scenario,
  actualFps,
  targetFps,
  ticSkip,
  systemRunning = true,
  onTraining,
  onSystemControl,
  onSwitchScenario,
  onUpdateSpeed,
  onResetEpisode,
}) {
  if (!policy) return null;

  const isRunning = policy.system_running ?? systemRunning;
  const history = policy.history || [];
  const rewards = history.map((h) => Number(h.reward) || 0);
  const losses = history.map((h) => Number(h.loss) || 0);
  const scenarios = scenario?.available_scenarios || [];
  const currentScenarioId = scenario?.id || policy.scenario_id || "defend_the_center";
  const currentFps = actualFps ?? policy.actual_fps ?? 0;
  const currentTargetFps = targetFps ?? policy.target_fps ?? 30;
  const currentTicSkip = ticSkip ?? policy.tic_skip ?? 2;
  const explPct = ((policy.exploration_rate ?? 0) * 100).toFixed(0);

  const stats = [
    { label: "EPISODIOS", value: policy.episodes ?? 0, tone: "text-[#ffffff]" },
    { label: "RECOMP. MEDIA", value: (policy.avg_reward ?? 0).toFixed(2), tone: "text-[#34a853]" },
    { label: "LOSS PPO", value: (policy.last_loss ?? 0).toFixed(4), tone: "text-[#fbbc05]" },
    { label: "EXPLORACIÓN", value: `${explPct}%`, tone: "text-[#448cff]" },
    { label: "FPS REAL", value: `${Number(currentFps).toFixed(1)}`, tone: "text-[#34a853]" },
    { label: "BAJAS", value: policy.total_kills ?? 0, tone: "text-[#ea4335]" },
  ];

  const send = (payload) => onTraining && onTraining(payload);

  return (
    <div className="bg-[#252525] border border-[#383838] rounded-xl p-4 space-y-3 font-mono text-xs">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[#34a853] uppercase font-semibold">
          Control {policy.algorithm || "PPO-CNN"}
        </span>
        <span
          style={{
            backgroundColor: !isRunning
              ? "rgba(251, 188, 5, 0.15)"
              : policy.training_enabled
              ? "rgba(52, 168, 83, 0.15)"
              : "rgba(251, 188, 5, 0.15)",
          }}
          className={`px-2 py-0.5 rounded border text-[10px] ${
            !isRunning
              ? "border-[#fbbc05]/50 text-[#fbbc05]"
              : policy.training_enabled
              ? "border-[#34a853]/50 text-[#34a853]"
              : "border-[#fbbc05]/50 text-[#fbbc05]"
          }`}
        >
          {!isRunning ? "PAUSA · GUARDADO" : policy.training_enabled ? "ENTRENANDO" : "PAUSADO"}
        </span>
      </div>

      {/* Selector de escenario en caliente */}
      {scenarios.length > 0 && (
        <div className="bg-[#181818] border border-[#383838] rounded-lg p-2.5 space-y-1.5">
          <div className="flex items-center justify-between text-[10px] text-[#c1c1c1]">
            <span className="flex items-center gap-1 text-[#448cff] font-semibold">
              <Layers className="w-3 h-3" /> ESCENARIO VIZDOOM EN CALIENTE
            </span>
            <span>{scenario?.actions?.length ?? policy.n_actions ?? 4} acc.</span>
          </div>
          <select
            value={currentScenarioId}
            onChange={(e) => onSwitchScenario?.(e.target.value)}
            className="w-full bg-[#212121] border border-[#383838] rounded px-2 py-1.5 text-xs text-[#ffffff] focus:outline-none focus:border-[#448cff]"
          >
            {scenarios.map((sc) => (
              <option key={sc.id} value={sc.id}>
                {sc.name} ({sc.cfg_file})
              </option>
            ))}
          </select>
          {scenario?.description && (
            <p className="text-[10px] text-[#c1c1c1] leading-snug">{scenario.description}</p>
          )}
        </div>
      )}

      {/* KPIs en tiempo real */}
      <div className="grid grid-cols-3 gap-2">
        {stats.map((s) => (
          <div key={s.label} className="bg-[#181818] border border-[#383838] rounded-lg p-2">
            <div className="text-[9px] text-[#c1c1c1] leading-tight">{s.label}</div>
            <div className={`text-sm font-bold ${s.tone}`}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Controles de velocidad de simulación */}
      <div className="bg-[#181818] border border-[#383838] rounded-lg p-2.5 space-y-2">
        <div className="flex items-center justify-between text-[10px] text-[#c1c1c1]">
          <span className="flex items-center gap-1 text-[#34a853] font-semibold">
            <Gauge className="w-3 h-3" /> VELOCIDAD DE SIMULACIÓN
          </span>
          <span>
            {currentTargetFps} Hz · Skip {currentTicSkip}x
          </span>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <label className="space-y-1 text-[10px] text-[#c1c1c1]">
            <div className="flex justify-between">
              <span>Target FPS</span>
              <span className="text-[#ffffff]">{currentTargetFps}</span>
            </div>
            <input
              type="range"
              min="5"
              max="60"
              step="5"
              value={currentTargetFps}
              onChange={(e) => onUpdateSpeed?.({ target_fps: Number(e.target.value) })}
              className="w-full accent-[#34a853]"
            />
          </label>
          <label className="space-y-1 text-[10px] text-[#c1c1c1]">
            <div className="flex justify-between">
              <span>Tic Skip</span>
              <span className="text-[#ffffff]">{currentTicSkip}</span>
            </div>
            <input
              type="range"
              min="1"
              max="8"
              step="1"
              value={currentTicSkip}
              onChange={(e) => onUpdateSpeed?.({ tic_skip: Number(e.target.value) })}
              className="w-full accent-[#448cff]"
            />
          </label>
        </div>
      </div>

      {/* Gráficas en tiempo real: Recompensa y Loss */}
      <div className="space-y-2">
        <div>
          <div className="flex items-center justify-between text-[10px] text-[#c1c1c1] mb-1">
            <span>RECOMPENSA ACUMULADA / EPISODIO</span>
            <span>{history.length} eps</span>
          </div>
          <MiniSeriesChart
            values={rewards}
            stroke="#34a853"
            fill="rgba(52, 168, 83, 0.15)"
            emptyText="Esperando episodios completados..."
          />
        </div>
        <div>
          <div className="flex items-center justify-between text-[10px] text-[#c1c1c1] mb-1">
            <span>PÉRDIDA PPO (POLICY + VALUE)</span>
            <span>
              PG {(policy.policy_loss ?? 0).toFixed(3)} · VF {(policy.value_loss ?? 0).toFixed(3)}
            </span>
          </div>
          <MiniSeriesChart
            values={losses}
            stroke="#fbbc05"
            fill="rgba(251, 188, 5, 0.12)"
            emptyText={`Rollout ${policy.rollout_progress ?? 0}/${policy.rollout_steps ?? 128}...`}
          />
        </div>
      </div>

      {/* Botones de control de simulación */}
      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={() => onSystemControl?.({ running: !isRunning, save: true })}
          style={{
            backgroundColor: isRunning
              ? "rgba(251, 188, 5, 0.15)"
              : "rgba(52, 168, 83, 0.15)",
          }}
          className={`flex items-center justify-center gap-1.5 px-2.5 py-2 rounded-lg border font-bold transition ${
            isRunning
              ? "border-[#fbbc05]/60 text-[#fbbc05] hover:border-[#fbbc05]"
              : "border-[#34a853] text-[#34a853] hover:bg-[#34a853] hover:text-[#ffffff]"
          }`}
        >
          {isRunning ? (
            <>
              <Power className="w-3.5 h-3.5" />
              Pausar y Guardar
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5" />
              Reanudar Sistema
            </>
          )}
        </button>
        <button
          onClick={() => onResetEpisode?.()}
          style={{ backgroundColor: "rgba(66, 133, 244, 0.15)" }}
          className="flex items-center justify-center gap-1.5 px-2.5 py-2 rounded-lg border border-[#4285f4]/50 hover:border-[#448cff] text-[#448cff] transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Reiniciar Episodio
        </button>
      </div>

      <div className="grid grid-cols-4 gap-1.5">
        <button
          onClick={() => send({ enabled: !policy.training_enabled })}
          className="flex items-center justify-center gap-1 px-1.5 py-2 rounded-lg bg-[#181818] border border-[#383838] hover:border-[#34a853] text-[#ffffff] transition text-[11px]"
        >
          {policy.training_enabled ? (
            <Pause className="w-3 h-3 text-[#fbbc05]" />
          ) : (
            <Play className="w-3 h-3 text-[#34a853]" />
          )}
          {policy.training_enabled ? "Pausar RL" : "Entrenar"}
        </button>
        <button
          onClick={() => send({ greedy: !policy.greedy })}
          className="flex items-center justify-center gap-1 px-1.5 py-2 rounded-lg bg-[#181818] border border-[#383838] hover:border-[#4285f4] text-[#ffffff] transition text-[11px]"
        >
          <Target className="w-3 h-3 text-[#448cff]" />
          {policy.greedy ? "Explorar" : "Greedy"}
        </button>
        <button
          onClick={() => onSystemControl?.({ save: true })}
          className="flex items-center justify-center gap-1 px-1.5 py-2 rounded-lg bg-[#181818] border border-[#383838] hover:border-[#448cff] text-[#ffffff] transition text-[11px]"
        >
          <Save className="w-3 h-3 text-[#448cff]" />
          Guardar
        </button>
        <button
          onClick={() => send({ reset: true })}
          title="Reinicia pesos PPO y contadores del escenario actual"
          className="flex items-center justify-center gap-1 px-1.5 py-2 rounded-lg bg-[#181818] border border-[#383838] hover:border-[#ea4335] text-[#ffffff] transition text-[11px]"
        >
          <RotateCcw className="w-3 h-3 text-[#ea4335]" />
          Reset 0
        </button>
      </div>

      <div className="flex items-center justify-between text-[10px] text-[#c1c1c1]">
        <span className="flex items-center gap-1">
          <Activity className="w-3 h-3 text-[#4285f4]" />
          rollout {policy.rollout_progress ?? 0}/{policy.rollout_steps ?? 128} · upd {policy.updates ?? 0}
        </span>
        <span className="flex items-center gap-1">
          <Skull className="w-3 h-3 text-[#ea4335]" /> {policy.total_kills ?? 0} bajas ·{" "}
          <Crosshair className="w-3 h-3 text-[#34a853]" />{" "}
          {((policy.accuracy ?? 0) * 100).toFixed(0)}%
        </span>
      </div>
    </div>
  );
}
