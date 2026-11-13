import React from "react";
import { REGION_HEX } from "./palette.js";

export default function RegionActivityList({ names = [], activity = {}, compact = false }) {
  return (
    <div className={compact ? "space-y-1" : "space-y-1.5"}>
      {names.map((name, index) => {
        const raw = activity[name] ?? 0;
        const intensity = Math.min(1, raw * 24);
        const width = Math.max(2, intensity * 100);
        return (
          <div key={name} className="group">
            <div className="flex items-center justify-between gap-2 font-mono text-[9px]">
              <span className="flex items-center gap-1.5 min-w-0">
                <span
                  className="inline-block w-1.5 h-1.5 rounded-full shrink-0"
                  style={{
                    backgroundColor: REGION_HEX[index] ?? "#64748b",
                    opacity: 0.45 + 0.55 * intensity,
                    boxShadow: intensity > 0.12 ? `0 0 6px ${REGION_HEX[index]}` : "none",
                  }}
                />
                <span className="text-slate-400 truncate group-hover:text-slate-200">{name}</span>
              </span>
              <span className={intensity > 0.12 ? "text-slate-200" : "text-slate-600"}>
                {raw.toFixed(4)}
              </span>
            </div>
            <div className="mt-0.5 h-1 rounded-full bg-slate-950 overflow-hidden">
              <div
                className="h-full rounded-full transition-[width] duration-200"
                style={{
                  width: `${width}%`,
                  backgroundColor: REGION_HEX[index] ?? "#64748b",
                  opacity: 0.35 + 0.65 * intensity,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
