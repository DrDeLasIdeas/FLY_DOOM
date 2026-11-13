import React from "react";

const COLORS = [
  "bg-cyan-400",
  "bg-sky-400",
  "bg-rose-500",
  "bg-emerald-400",
  "bg-amber-400",
  "bg-fuchsia-400",
  "bg-violet-400",
];

const DEFAULT_LABELS = [
  "Girar Izquierda",
  "Girar Derecha",
  "Disparar (DNp09)",
  "Reposo",
];

export default function ActionBars({
  probs = [],
  labels = DEFAULT_LABELS,
  actionIdx = -1,
  compact = false,
}) {
  const activeLabels = labels?.length ? labels : DEFAULT_LABELS;

  return (
    <div className={compact ? "space-y-1.5" : "space-y-2.5"}>
      {activeLabels.map((label, idx) => {
        const p = probs[idx] || 0;
        const active = actionIdx === idx;
        const color = COLORS[idx % COLORS.length];
        return (
          <div key={`${label}-${idx}`} className="space-y-1">
            <div className="flex justify-between text-[10px] font-mono">
              <span className={active ? "text-white font-bold" : "text-slate-300"}>
                {active ? "▶ " : ""}
                {label}
              </span>
              <span className="text-cyan-300">{(p * 100).toFixed(1)}%</span>
            </div>
            <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden">
              <div
                className={`h-full ${color} transition-all duration-75`}
                style={{ width: `${Math.min(100, p * 100)}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
