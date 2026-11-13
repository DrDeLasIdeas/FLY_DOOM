import React, { useState } from "react";
import { ArrowUpRight } from "lucide-react";
import ConnectomeScene from "./ConnectomeScene.jsx";
import { REGION_HEX } from "./palette.js";
import ConnectomeFallback from "./ConnectomeFallback.jsx";
import { useTopology } from "./useTopology.js";

const VIEW_OPTIONS = [
  { key: "mosca", label: "Mosca" },
  { key: "frontal", label: "Frontal" },
  { key: "explotada", label: "Explotada" },
];

export default function ConnectomePanel({
  connectome,
  neurons3d = [],
  attackPower = 0,
  compact = false,
  bare = false,
  onOpenStudio,
}) {
  const { topology, error } = useTopology();
  const [view, setView] = useState("mosca");
  const height = compact ? 168 : 262;
  const regionActivity = connectome?.region_activity ?? {};

  return (
    <div
      className={
        bare ? "flex flex-col" : "bg-slate-900/90 border border-slate-800 rounded-2xl p-4 flex flex-col"
      }
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="min-w-0">
          <div className="text-xs font-mono uppercase tracking-wider text-cyan-400 truncate">
            Topología 3D FlyWire
          </div>
          <div className="text-[10px] font-mono text-slate-500 truncate">
            {topology
              ? `${(topology.numNeurons ?? 20000).toLocaleString("es-MX")} neuronas · ${(
                  topology.numGhost ?? 0
                ).toLocaleString("es-MX")} ghost · ${topology.edges.length / 2} sinapsis`
              : "cargando conectoma anatómico..."}
          </div>
        </div>
        <div className="flex gap-1 shrink-0">
          {onOpenStudio && (
            <button
              type="button"
              onClick={onOpenStudio}
              className="flex items-center gap-0.5 px-1.5 py-0.5 rounded border border-violet-500/50 text-violet-300 bg-violet-500/10 hover:bg-violet-500/20 text-[9px] font-mono uppercase tracking-wide transition-colors"
              title="Abrir Conectoma 3D"
            >
              Studio
              <ArrowUpRight className="w-2.5 h-2.5" />
            </button>
          )}
          {VIEW_OPTIONS.map((option) => (
            <button
              key={option.key}
              type="button"
              onClick={() => setView(option.key)}
              className={`px-1.5 py-0.5 rounded border text-[9px] font-mono uppercase tracking-wide transition-colors ${
                view === option.key
                  ? "border-cyan-500/70 text-cyan-300 bg-cyan-500/10"
                  : "border-slate-700 text-slate-400 hover:border-slate-500"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div
        className="relative rounded-xl overflow-hidden border border-slate-800 bg-slate-950"
        style={{ height }}
      >
        {topology ? (
          <ConnectomeScene
            topology={topology}
            connectome={connectome}
            attackPower={attackPower}
            compact={compact}
            view={view}
          />
        ) : (
          <ConnectomeFallback neurons3d={neurons3d} attackPower={attackPower} error={error} />
        )}

        <div className="absolute left-2 bottom-2 flex flex-col gap-0.5 font-mono text-[9px] text-slate-400 pointer-events-none">
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-cyan-400" />
            excitatoria
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-fuchsia-400" />
            inhibitoria
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-amber-400" />
            dopamina (DAN)
          </span>
        </div>
      </div>

      {!compact && topology && (
        <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 font-mono text-[9px] text-slate-500">
          {topology.regionNames.map((name, index) => {
            const activity = Math.min(1, (regionActivity[name] ?? 0) * 24);
            return (
              <span key={name} className="flex items-center gap-1" title={name}>
                <span
                  className="inline-block w-1.5 h-1.5 rounded-full"
                  style={{
                    backgroundColor: REGION_HEX[index] ?? "#64748b",
                    opacity: 0.45 + 0.55 * activity,
                    boxShadow: activity > 0.15 ? `0 0 5px ${REGION_HEX[index]}` : "none",
                  }}
                />
                <span className={activity > 0.15 ? "text-slate-300" : ""}>{name}</span>
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}
