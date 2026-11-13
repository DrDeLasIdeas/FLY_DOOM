import React from "react";

const ACTIONS = [
  { idx: 0, label: "Girar Izquierda", color: "bg-cyan-400" },
  { idx: 1, label: "Girar Derecha", color: "bg-sky-400" },
  { idx: 2, label: "Disparar (DNp09)", color: "bg-rose-500" },
  { idx: 3, label: "Reposo", color: "bg-slate-500" },
];

export default function ActionBars({ probs = [], actionIdx = -1, compact = false }) {
  return (
    <div className={compact ? "space-y-1.5" : "space-y-2.5"}>
      {ACTIONS.map((a) => {
        const p = probs[a.idx] || 0;
        const active = actionIdx === a.idx;
        return (
          <div key={a.idx} className="space-y-1">
            <div className="flex justify-between text-[10px] font-mono">
              <span className={active ? "text-white font-bold" : "text-slate-300"}>
                {active ? "▶ " : ""}
                {a.label}
              </span>
              <span className="text-cyan-300">{(p * 100).toFixed(1)}%</span>
            </div>
            <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden">
              <div
                className={`h-full ${a.color} transition-all duration-75`}
                style={{ width: `${Math.min(100, p * 100)}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
