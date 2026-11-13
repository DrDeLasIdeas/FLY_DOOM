import React, { useMemo, useState } from "react";
import { Boxes, Cpu, HardDrive, Timer } from "lucide-react";

const DENSE_MB = (20000 * 20000 * 4) / 1e6;
const TARGET_MS = 15;
const LATENCY_PARTS = [
  { label: "retina", ms: 0.8, color: "#4285f4" },
  { label: "sparse mm", ms: 1.8, color: "#fbbc05" },
  { label: "LIF", ms: 1.2, color: "#34a853" },
  { label: "política", ms: 0.5, color: "#448cff" },
  { label: "WS 35 Hz", ms: 0.3, color: "#ea4335" },
];

export default function RuntimeWidget({ telemetry }) {
  const [nnz, setNnz] = useState(600000);
  const sparseMB = (nnz * 20) / 1e6;
  const ratio = DENSE_MB / sparseMB;
  const latency = telemetry?.biophysics?.latency_ms ?? 4.6;
  const device = telemetry?.biophysics?.device ?? "cpu";

  const scale = useMemo(
    () => (mb) => Math.max(2, (Math.log10(mb + 1) / Math.log10(DENSE_MB + 1)) * 100),
    [],
  );

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 space-y-2">
          <div className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-wider text-slate-500">
            <HardDrive className="w-3 h-3 text-amber-400" /> Matriz sináptica: densa vs dispersa
          </div>
          <div className="space-y-1.5 font-mono text-[9px]">
            <div>
              <div className="flex justify-between">
                <span className="text-rose-300">W densa · 20k² · float32</span>
                <span className="text-rose-200">{DENSE_MB.toFixed(0)} MB</span>
              </div>
              <div className="h-2 rounded-full bg-slate-900 overflow-hidden">
                <div className="h-full rounded-full bg-rose-500/80" style={{ width: `${scale(DENSE_MB)}%` }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between">
                <span className="text-emerald-300">W COO · {nnz.toLocaleString("es-MX")} nnz</span>
                <span className="text-emerald-200">{sparseMB.toFixed(1)} MB</span>
              </div>
              <div className="h-2 rounded-full bg-slate-900 overflow-hidden">
                <div
                  className="h-full rounded-full bg-emerald-500/80"
                  style={{ width: `${scale(sparseMB)}%` }}
                />
              </div>
            </div>
          </div>
          <label className="block font-mono text-[9px] text-slate-400">
            nnz <strong className="text-emerald-200">{nnz.toLocaleString("es-MX")}</strong>
            <input
              type="range"
              min="100000"
              max="1500000"
              step="50000"
              value={nnz}
              onChange={(event) => setNnz(Number(event.target.value))}
              className="w-full accent-emerald-400"
            />
          </label>
          <div className="flex justify-between font-mono text-[9px]">
            <span className="text-slate-500">factor de compresión</span>
            <span className="text-cyan-300">{ratio.toFixed(1)}×</span>
          </div>
          <div className="font-mono text-[8px] text-slate-600">
            PyTorch COO/CSR: 20 B por sinapsis (valor float32 + índices int64).
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 space-y-2">
          <div className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-wider text-slate-500">
            <Timer className="w-3 h-3 text-cyan-400" /> Presupuesto de latencia por paso
          </div>
          <div className="flex items-end justify-between">
            <div>
              <div className="font-mono text-[8px] text-slate-500">medido</div>
              <div className="font-mono text-2xl font-bold text-emerald-300">{latency.toFixed(1)} ms</div>
            </div>
            <div className="text-right">
              <div className="font-mono text-[8px] text-slate-500">objetivo</div>
              <div className="font-mono text-sm text-slate-300">&lt; {TARGET_MS} ms</div>
            </div>
          </div>
          <div className="space-y-1 font-mono text-[8px]">
            {LATENCY_PARTS.map((part) => (
              <div key={part.label}>
                <div className="flex justify-between text-slate-400">
                  <span>{part.label}</span>
                  <span>{part.ms.toFixed(1)} ms</span>
                </div>
                <div className="h-1.5 rounded-full bg-slate-900 overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.min(100, (part.ms / TARGET_MS) * 100)}%`,
                      backgroundColor: part.color,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="flex justify-between font-mono text-[8px] text-slate-500 pt-1 border-t border-slate-800">
            <span>dispositivo</span>
            <span className={device === "cpu" ? "text-amber-300" : "text-emerald-300"}>{device}</span>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
        <div className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-wider text-slate-500 mb-2">
          <Boxes className="w-3 h-3 text-violet-400" /> Orquestación híbrida ARM64
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[8px]">
          {[
            { title: "ViZDoom", detail: "C++ · 320×240", tone: "border-rose-500/40 text-rose-200" },
            { title: "Retina", detail: "64×64 · 4,096", tone: "border-cyan-500/40 text-cyan-200" },
            { title: "SNN LIF", detail: "20k · COO sparse", tone: "border-violet-500/40 text-violet-200" },
            { title: "R-STDP", detail: "PAM / PPL1", tone: "border-fuchsia-500/40 text-fuchsia-200" },
            { title: "FastAPI", detail: "WS 35 Hz", tone: "border-emerald-500/40 text-emerald-200" },
            { title: "Gemma 3", detail: "Ollama host", tone: "border-amber-500/40 text-amber-200" },
            { title: "Docker", detail: "linux/arm64", tone: "border-sky-500/40 text-sky-200" },
            { title: "Dashboard", detail: "React + R3F", tone: "border-slate-500/40 text-slate-200" },
          ].map((box) => (
            <div key={box.title} className={`rounded-lg border bg-slate-900/60 p-2 ${box.tone}`}>
              <div className="font-bold">{box.title}</div>
              <div className="text-slate-500">{box.detail}</div>
            </div>
          ))}
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2 font-mono text-[8px] text-slate-500">
          <span className="flex items-center gap-1">
            <Cpu className="w-3 h-3 text-cyan-400" /> CPU NEON para sparse mm
          </span>
          <span className="text-slate-700">·</span>
          <span>Metal reservado para Ollama / Gemma 3</span>
          <span className="text-slate-700">·</span>
          <span>un solo `docker compose up --build`</span>
        </div>
      </div>
    </div>
  );
}
