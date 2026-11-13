import React, { useState } from "react";
import { BrainCircuit, Clock, Cpu, Sparkles } from "lucide-react";

const CLAMP_MIN = -49;
const CLAMP_MAX = -41;

export default function GemmaWidget({ telemetry }) {
  const [proposed, setProposed] = useState(-44.5);
  const clamped = Math.min(CLAMP_MAX, Math.max(CLAMP_MIN, proposed));
  const gemma = telemetry?.gemma;
  const vThresh = telemetry?.biophysics?.v_thresh;
  const markerPercent = ((proposed - CLAMP_MIN) / (CLAMP_MAX - CLAMP_MIN)) * 100;
  const clampedPercent = ((clamped - CLAMP_MIN) / (CLAMP_MAX - CLAMP_MIN)) * 100;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 space-y-2">
          <div className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-wider text-slate-500">
            <Clock className="w-3 h-3 text-cyan-400" /> Escalas temporales acopladas
          </div>
          <div className="relative h-16 rounded-lg border border-slate-800 bg-slate-900/60 overflow-hidden">
            <div className="absolute inset-x-3 top-4 h-1 rounded-full bg-cyan-500/30" />
            {Array.from({ length: 41 }).map((_, index) => (
              <div
                key={index}
                className="absolute top-2.5 w-px h-4 bg-cyan-400/70"
                style={{ left: `${4 + index * 2.3}%` }}
              />
            ))}
            <div className="absolute inset-x-3 top-10 h-1 rounded-full bg-fuchsia-500/30" />
            {[0, 1, 2].map((index) => (
              <div
                key={index}
                className="absolute top-8 w-2 h-5 rounded-sm bg-fuchsia-400 shadow-[0_0_8px_rgba(232,121,249,0.8)]"
                style={{ left: `${4 + index * 45}%` }}
              />
            ))}
            <div className="absolute left-3 top-0.5 font-mono text-[8px] text-cyan-300">
              SNN · Δt = 1 ms · 4 sub-pasos
            </div>
            <div className="absolute left-3 bottom-0.5 font-mono text-[8px] text-fuchsia-300">
              Gemma 3 · cada 5 s
            </div>
          </div>
          <div className="grid grid-cols-3 gap-1 font-mono text-[8px] text-slate-400">
            <div className="rounded border border-slate-800 p-1.5">
              <div className="text-slate-600">bucle SNN</div>
              <div className="text-cyan-300">1 ms</div>
            </div>
            <div className="rounded border border-slate-800 p-1.5">
              <div className="text-slate-600">Gemma</div>
              <div className="text-fuchsia-300">5 s</div>
            </div>
            <div className="rounded border border-slate-800 p-1.5">
              <div className="text-slate-600">ratio</div>
              <div className="text-amber-300">5000×</div>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 space-y-2">
          <div className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-wider text-slate-500">
            <Cpu className="w-3 h-3 text-amber-400" /> Clamp homeostático de V_th
          </div>
          <div className="relative pt-5 pb-2">
            <div className="h-2 rounded-full bg-gradient-to-r from-rose-500 via-amber-400 to-emerald-400" />
            <div
              className="absolute top-3 w-0.5 h-6 bg-white shadow-[0_0_8px_rgba(255,255,255,0.9)]"
              style={{ left: `${markerPercent}%` }}
            />
            <div
              className="absolute top-2 -translate-x-1/2 px-1 rounded bg-slate-800 border border-slate-600 font-mono text-[8px] text-slate-200"
              style={{ left: `${clampedPercent}%` }}
            >
              {clamped.toFixed(2)}
            </div>
          </div>
          <div className="flex justify-between font-mono text-[8px] text-slate-500">
            <span>{CLAMP_MIN} mV</span>
            <span className="text-amber-300">banda segura</span>
            <span>{CLAMP_MAX} mV</span>
          </div>
          <label className="block font-mono text-[9px] text-slate-400">
            Propuesta de Gemma: <strong className="text-cyan-200">{proposed.toFixed(2)} mV</strong>
            <input
              type="range"
              min="-55"
              max="-35"
              step="0.1"
              value={proposed}
              onChange={(event) => setProposed(Number(event.target.value))}
              className="w-full accent-cyan-400"
            />
          </label>
          <div className="font-mono text-[8px] text-slate-500">
            La propuesta se recorta antes de tocar el conectoma.
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[9px]">
        <div className="rounded border border-slate-800 bg-slate-950 p-2">
          <div className="text-slate-600">V_th vivo</div>
          <div className="text-emerald-300">{vThresh ?? "—"} mV</div>
        </div>
        <div className="rounded border border-slate-800 bg-slate-950 p-2">
          <div className="text-slate-600">modelo</div>
          <div className="text-fuchsia-300 truncate">{gemma?.model ?? "gemma3:4b"}</div>
        </div>
        <div className="rounded border border-slate-800 bg-slate-950 p-2">
          <div className="text-slate-600">estado</div>
          <div className={gemma?.status?.includes("ONLINE") ? "text-emerald-300" : "text-amber-300"}>
            {gemma?.status ?? "esperando"}
          </div>
        </div>
        <div className="rounded border border-slate-800 bg-slate-950 p-2">
          <div className="text-slate-600">η_da</div>
          <div className="text-cyan-300">{gemma?.dopamine_lr ?? "—"}</div>
        </div>
      </div>

      <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-3 space-y-1">
        <div className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-wider text-emerald-300">
          <Sparkles className="w-3 h-3" /> Hipótesis neuroquímica en vivo
        </div>
        <p className="text-[11px] leading-relaxed text-emerald-100/90">
          {gemma?.neuro_hypothesis ??
            "El regulador cortical analizará la tasa de Kenyon y el error de recompensa para proponer un umbral homeostático."}
        </p>
        <div className="flex items-center gap-2 font-mono text-[8px] text-emerald-200/70">
          <BrainCircuit className="w-3 h-3" />
          Sistema 2 asíncrono · nunca bloquea el WebSocket de 35 Hz
        </div>
      </div>
    </div>
  );
}
