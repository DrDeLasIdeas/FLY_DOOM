import React, { useMemo, useState } from "react";
import { Activity, Gauge, Zap } from "lucide-react";

const V_REST = -52;
const V_RESET = -58;
const R_MEMBRANE = 1.0;
const T_MS = 220;

function simulate({ current, tau, threshold }) {
  const dt = 1;
  const values = [];
  const spikes = [];
  let v = V_REST;
  let refractory = 0;
  for (let t = 0; t < T_MS; t += 1) {
    if (refractory > 0) {
      refractory -= 1;
      values.push(V_RESET);
      continue;
    }
    const dv = (-(v - V_REST) + R_MEMBRANE * current) / tau;
    v += dv * dt;
    if (v >= threshold) {
      spikes.push(t);
      v = V_RESET;
      refractory = 2;
    }
    values.push(v);
  }
  return { values, spikes, rate: spikes.length / (T_MS / 1000) };
}

export default function LifWidget({ telemetry }) {
  const [current, setCurrent] = useState(9.5);
  const [tau, setTau] = useState(20);
  const [threshold, setThreshold] = useState(-45);
  const sim = useMemo(
    () => simulate({ current, tau, threshold }),
    [current, tau, threshold],
  );

  const width = 620;
  const height = 240;
  const pad = { left: 42, right: 12, top: 14, bottom: 26 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const vMin = -72;
  const vMax = -34;
  const xOf = (t) => pad.left + (t / (T_MS - 1)) * innerW;
  const yOf = (v) => pad.top + ((vMax - v) / (vMax - vMin)) * innerH;
  const points = sim.values
    .map((v, t) => `${xOf(t).toFixed(1)},${yOf(v).toFixed(1)}`)
    .join(" ");
  const steady = V_REST + R_MEMBRANE * current;
  const firing = sim.rate > 0;

  return (
    <div className="space-y-3">
      <div className="rounded-xl border border-slate-800 bg-slate-950 p-2">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
          <defs>
            <linearGradient id="lif-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#4285f4" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#4285f4" stopOpacity="0" />
            </linearGradient>
          </defs>
          {[-70, -60, -50, -40].map((tick) => (
            <g key={tick}>
              <line
                x1={pad.left}
                x2={width - pad.right}
                y1={yOf(tick)}
                y2={yOf(tick)}
                stroke="#383838"
                strokeDasharray="2 4"
              />
              <text x={pad.left - 6} y={yOf(tick) + 3} textAnchor="end" fill="#c1c1c1" fontSize="8">
                {tick}
              </text>
            </g>
          ))}
          <line
            x1={pad.left}
            x2={width - pad.right}
            y1={yOf(threshold)}
            y2={yOf(threshold)}
            stroke="#fbbc05"
            strokeWidth="1.4"
            strokeDasharray="6 3"
          />
          <text x={width - pad.right} y={yOf(threshold) - 4} textAnchor="end" fill="#fbbc05" fontSize="8">
            V_th {threshold.toFixed(1)} mV
          </text>
          <line
            x1={pad.left}
            x2={width - pad.right}
            y1={yOf(V_REST)}
            y2={yOf(V_REST)}
            stroke="#383838"
            strokeWidth="1"
          />
          <text x={pad.left + 2} y={yOf(V_REST) - 4} fill="#c1c1c1" fontSize="8">
            V_rest {V_REST} mV
          </text>

          <polygon
            points={`${pad.left},${pad.top + innerH} ${points} ${width - pad.right},${pad.top + innerH}`}
            fill="url(#lif-fill)"
          />
          <polyline points={points} fill="none" stroke="#4285f4" strokeWidth="1.8" />

          {sim.spikes.map((t) => (
            <g key={t}>
              <line
                x1={xOf(t)}
                x2={xOf(t)}
                y1={pad.top + innerH}
                y2={pad.top + innerH - 9}
                stroke="#ea4335"
                strokeWidth="1.6"
              />
              <circle cx={xOf(t)} cy={yOf(threshold)} r="2.6" fill="#ea4335" />
            </g>
          ))}

          <text x={pad.left} y={height - 8} fill="#c1c1c1" fontSize="8">
            0 ms
          </text>
          <text x={width - pad.right} y={height - 8} textAnchor="end" fill="#c1c1c1" fontSize="8">
            {T_MS} ms
          </text>
        </svg>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[9px]">
        <div className="rounded border border-slate-800 bg-slate-950 p-2">
          <div className="text-slate-600">I_ext</div>
          <div className="text-cyan-300">{current.toFixed(1)} nA</div>
        </div>
        <div className="rounded border border-slate-800 bg-slate-950 p-2">
          <div className="text-slate-600">V∞ = V_rest + R·I</div>
          <div className={steady >= threshold ? "text-amber-300" : "text-slate-300"}>
            {steady.toFixed(1)} mV
          </div>
        </div>
        <div className="rounded border border-slate-800 bg-slate-950 p-2">
          <div className="text-slate-600">tasa</div>
          <div className={firing ? "text-fuchsia-300" : "text-slate-500"}>
            {sim.rate.toFixed(1)} Hz
          </div>
        </div>
        <div className="rounded border border-slate-800 bg-slate-950 p-2">
          <div className="text-slate-600">spikes / 220 ms</div>
          <div className={firing ? "text-amber-300" : "text-slate-500"}>{sim.spikes.length}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <label className="block font-mono text-[9px] text-slate-400">
          <span className="flex items-center gap-1">
            <Zap className="w-3 h-3 text-cyan-300" /> I_ext{" "}
            <strong className="text-cyan-200">{current.toFixed(1)} nA</strong>
          </span>
          <input
            type="range"
            min="0"
            max="18"
            step="0.1"
            value={current}
            onChange={(event) => setCurrent(Number(event.target.value))}
            className="w-full accent-cyan-400"
          />
        </label>
        <label className="block font-mono text-[9px] text-slate-400">
          <span className="flex items-center gap-1">
            <Activity className="w-3 h-3 text-emerald-300" /> τ_m{" "}
            <strong className="text-emerald-200">{tau} ms</strong>
          </span>
          <input
            type="range"
            min="5"
            max="40"
            step="1"
            value={tau}
            onChange={(event) => setTau(Number(event.target.value))}
            className="w-full accent-emerald-400"
          />
        </label>
        <label className="block font-mono text-[9px] text-slate-400">
          <span className="flex items-center gap-1">
            <Gauge className="w-3 h-3 text-amber-300" /> V_th{" "}
            <strong className="text-amber-200">{threshold.toFixed(1)} mV</strong>
          </span>
          <input
            type="range"
            min="-55"
            max="-38"
            step="0.5"
            value={threshold}
            onChange={(event) => setThreshold(Number(event.target.value))}
            className="w-full accent-amber-400"
          />
        </label>
      </div>

      <div className="flex flex-wrap gap-2 font-mono text-[9px]">
        <span className="px-2 py-1 rounded border border-slate-700 bg-slate-950 text-slate-400">
          V_rest {telemetry?.biophysics?.v_rest ?? V_REST} mV
        </span>
        <span className="px-2 py-1 rounded border border-slate-700 bg-slate-950 text-slate-400">
          τ_syn {telemetry?.biophysics?.tau_syn ?? 5} ms
        </span>
        <span className="px-2 py-1 rounded border border-slate-700 bg-slate-950 text-slate-400">
          sub-pasos {telemetry?.biophysics?.substeps ?? 4}
        </span>
        <span
          className={`px-2 py-1 rounded border font-semibold ${
            firing
              ? "border-fuchsia-500/60 bg-fuchsia-500/10 text-fuchsia-200"
              : "border-slate-700 bg-slate-950 text-slate-500"
          }`}
        >
          {firing ? "RÉGIMEN TÓNICO" : "SUBUMBRAL"}
        </span>
      </div>
    </div>
  );
}
