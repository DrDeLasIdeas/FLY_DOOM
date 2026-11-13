import React from "react";
import { Skull } from "lucide-react";

export default function KillFeed({ events = [] }) {
  if (!events.length) {
    return (
      <div className="text-[10px] font-mono text-slate-500 border border-dashed border-slate-800 rounded-lg p-3 text-center">
        Sin bajas registradas todavía.
      </div>
    );
  }
  return (
    <ul className="space-y-1.5 font-mono text-[10px]">
      {events.map((e) => (
        <li
          key={e.id}
          className="flex items-center justify-between gap-2 rounded-lg bg-slate-950 border border-rose-500/30 px-2 py-1"
        >
          <span className="flex items-center gap-1.5 text-rose-300">
            <Skull className="w-3 h-3" /> BAJA #{e.totalKills}
          </span>
          <span className="text-slate-400">
            ep {e.episode} · {e.time}
          </span>
        </li>
      ))}
    </ul>
  );
}
