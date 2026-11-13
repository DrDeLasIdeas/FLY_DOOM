import React from "react";

export default function BarChart({ items = [], scale = 1, suffix = "%" }) {
  return (
    <div className="space-y-2">
      {items.map((item) => {
        const pct = Math.max(0, Math.min(100, (item.value ?? 0) * scale * 100));
        return (
          <div key={item.label} className="space-y-1">
            <div className="flex justify-between text-[10px] font-mono">
              <span className={item.active ? "text-white font-bold" : "text-slate-300"}>
                {item.active ? "▶ " : ""}
                {item.label}
              </span>
              <span className="text-cyan-300">
                {pct.toFixed(1)}
                {suffix}
              </span>
            </div>
            <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden">
              <div
                className={`h-full ${item.color || "bg-cyan-400"} transition-all duration-75`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
