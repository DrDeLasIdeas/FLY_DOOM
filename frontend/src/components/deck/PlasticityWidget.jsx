import React, { useMemo, useState } from "react";
import { ThumbsDown, ThumbsUp, TrendingUp } from "lucide-react";

const TRIALS = 80;

function simulate({ reward, punishment, eta, lambda }) {
  const weights = [];
  let w = 0.22;
  let eligibility = 0;
  for (let t = 0; t < TRIALS; t += 1) {
    const pre = 0.55 + 0.45 * Math.sin(t / 6.5);
    const post = 1;
    eligibility = lambda * eligibility + pre * post * 0.18;
    const dopamine = reward - punishment;
    w = Math.min(0.98, Math.max(0.02, w + eta * dopamine * eligibility));
    weights.push(w);
  }
  return { weights, final: weights[weights.length - 1] ?? w };
}

export default function PlasticityWidget({ telemetry, onDopaminePulse }) {
  const [reward, setReward] = useState(0.62);
  const [punishment, setPunishment] = useState(0.18);
  const [eta, setEta] = useState(0.02);
  const [lambda, setLambda] = useState(0.9);
  const sim = useMemo(
    () => simulate({ reward, punishment, eta, lambda }),
    [reward, punishment, eta, lambda],
  );

  const width = 520;
  const height = 150;
  const pad = { left: 30, right: 10, top: 10, bottom: 18 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const points = sim.weights
    .map((w, t) => {
      const x = pad.left + (t / (TRIALS - 1)) * innerW;
      const y = pad.top + (1 - w) * innerH;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  const deltaW = sim.final - 0.22;
  const da = reward - punishment;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] gap-3">
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-2">
          <svg viewBox="0 0 260 210" className="w-full h-auto">
            <defs>
              <marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
                <path d="M0,0 L7,3.5 L0,7 z" fill="#c1c1c1" />
              </marker>
              <marker id="arrow-da" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
                <path d="M0,0 L7,3.5 L0,7 z" fill="#34a853" />
              </marker>
            </defs>

            <text x="10" y="14" fill="#c1c1c1" fontSize="8" fontFamily="monospace">
              CUERPO SETIFORME
            </text>

            {[0, 1, 2, 3, 4].map((index) => {
              const y = 36 + index * 26;
              return (
                <g key={index}>
                  <circle cx="42" cy={y} r="8" fill="rgba(251, 188, 5, 0.15)" stroke="#fbbc05" strokeWidth="1.2" />
                  <text x="42" y={y + 3} textAnchor="middle" fill="#fbbc05" fontSize="7">
                    KC
                  </text>
                  <line
                    x1="50"
                    y1={y}
                    x2="142"
                    y2="92"
                    stroke="#383838"
                    strokeWidth="0.9"
                    markerEnd="url(#arrow)"
                  />
                </g>
              );
            })}

            <circle cx="158" cy="92" r="18" fill="rgba(66, 133, 244, 0.15)" stroke="#4285f4" strokeWidth="1.2" />
            <text x="158" y="90" textAnchor="middle" fill="#ffffff" fontSize="7">
              MBON
            </text>
            <text x="158" y="99" textAnchor="middle" fill="#448cff" fontSize="6">
              salida
            </text>

            <circle
              cx="206"
              cy="52"
              r="12"
              fill="rgba(52, 168, 83, 0.15)"
              stroke="#34a853"
              strokeWidth="1.2"
              opacity={0.45 + 0.55 * reward}
            />
            <text x="206" y="55" textAnchor="middle" fill="#34a853" fontSize="6">
              PAM
            </text>
            <circle
              cx="206"
              cy="132"
              r="12"
              fill="rgba(234, 67, 53, 0.15)"
              stroke="#ea4335"
              strokeWidth="1.2"
              opacity={0.45 + 0.55 * punishment}
            />
            <text x="206" y="135" textAnchor="middle" fill="#ea4335" fontSize="6">
              PPL1
            </text>

            <line
              x1="176"
              y1="86"
              x2="194"
              y2="60"
              stroke="#34a853"
              strokeWidth="1.2"
              strokeDasharray="3 2"
              markerEnd="url(#arrow-da)"
              opacity={0.5 + 0.5 * reward}
            />
            <line
              x1="176"
              y1="100"
              x2="194"
              y2="124"
              stroke="#ea4335"
              strokeWidth="1.2"
              strokeDasharray="3 2"
              markerEnd="url(#arrow-da)"
              opacity={0.5 + 0.5 * punishment}
            />

            <text x="132" y="186" fill="#34a853" fontSize="7" fontFamily="monospace">
              DA = r_PAM − r_PPL1 = {(da).toFixed(2)}
            </text>
            <text x="132" y="198" fill="#c1c1c1" fontSize="7" fontFamily="monospace">
              tercer factor modula E_ij
            </text>
          </svg>
        </div>

        <div className="space-y-2">
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-2">
            <div className="flex items-center justify-between font-mono text-[9px]">
              <span className="text-slate-500">Peso sináptico W_KC→MBON</span>
              <span className="text-violet-300">
                <TrendingUp className="inline w-3 h-3 mr-0.5" />
                {sim.final.toFixed(3)}
              </span>
            </div>
            <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
              {[0, 0.25, 0.5, 0.75, 1].map((tick) => {
                const y = pad.top + (1 - tick) * innerH;
                return (
                  <g key={tick}>
                    <line
                      x1={pad.left}
                      x2={width - pad.right}
                      y1={y}
                      y2={y}
                      stroke="#383838"
                      strokeDasharray="2 4"
                    />
                    <text x={pad.left - 4} y={y + 3} textAnchor="end" fill="#c1c1c1" fontSize="7">
                      {tick}
                    </text>
                  </g>
                );
              })}
              <polyline points={points} fill="none" stroke="#ea4335" strokeWidth="1.8" />
              <circle
                cx={pad.left + innerW}
                cy={pad.top + (1 - sim.final) * innerH}
                r="3"
                fill="#ea4335"
              />
              <text x={pad.left} y={height - 4} fill="#c1c1c1" fontSize="7">
                0
              </text>
              <text x={width - pad.right} y={height - 4} textAnchor="end" fill="#c1c1c1" fontSize="7">
                {TRIALS} ensayos
              </text>
            </svg>
          </div>
          <div className="grid grid-cols-3 gap-1 font-mono text-[9px]">
            <div className="rounded border border-slate-800 bg-slate-950 p-1.5">
              <div className="text-slate-600">ΔW</div>
              <div className={deltaW >= 0 ? "text-emerald-300" : "text-rose-300"}>
                {deltaW >= 0 ? "+" : ""}
                {deltaW.toFixed(3)}
              </div>
            </div>
            <div className="rounded border border-slate-800 bg-slate-950 p-1.5">
              <div className="text-slate-600">DA</div>
              <div className={da >= 0 ? "text-amber-300" : "text-rose-300"}>{da.toFixed(2)}</div>
            </div>
            <div className="rounded border border-slate-800 bg-slate-950 p-1.5">
              <div className="text-slate-600">λ</div>
              <div className="text-slate-300">{lambda.toFixed(2)}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <label className="block font-mono text-[9px] text-slate-400">
          <span className="flex items-center gap-1">
            <ThumbsUp className="w-3 h-3 text-emerald-300" /> r_PAM{" "}
            <strong className="text-emerald-200">{reward.toFixed(2)}</strong>
          </span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={reward}
            onChange={(event) => setReward(Number(event.target.value))}
            className="w-full accent-emerald-400"
          />
        </label>
        <label className="block font-mono text-[9px] text-slate-400">
          <span className="flex items-center gap-1">
            <ThumbsDown className="w-3 h-3 text-rose-300" /> r_PPL1{" "}
            <strong className="text-rose-200">{punishment.toFixed(2)}</strong>
          </span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={punishment}
            onChange={(event) => setPunishment(Number(event.target.value))}
            className="w-full accent-rose-400"
          />
        </label>
        <label className="block font-mono text-[9px] text-slate-400">
          <span className="flex items-center justify-between">
            <span>η_da</span>
            <strong className="text-cyan-200">{eta.toFixed(3)}</strong>
          </span>
          <input
            type="range"
            min="0.005"
            max="0.05"
            step="0.001"
            value={eta}
            onChange={(event) => setEta(Number(event.target.value))}
            className="w-full accent-cyan-400"
          />
        </label>
        <label className="block font-mono text-[9px] text-slate-400">
          <span className="flex items-center justify-between">
            <span>λ elegibilidad</span>
            <strong className="text-violet-200">{lambda.toFixed(2)}</strong>
          </span>
          <input
            type="range"
            min="0.5"
            max="0.99"
            step="0.01"
            value={lambda}
            onChange={(event) => setLambda(Number(event.target.value))}
            className="w-full accent-violet-400"
          />
        </label>
      </div>

      <div className="flex flex-wrap items-center gap-2 font-mono text-[9px]">
        <button
          onClick={() => onDopaminePulse?.(2.0)}
          className="px-2 py-1 rounded border border-emerald-500/50 bg-emerald-500/10 text-emerald-200 hover:bg-emerald-500/20"
        >
          + PAM 2.0
        </button>
        <button
          onClick={() => onDopaminePulse?.(-2.0)}
          className="px-2 py-1 rounded border border-rose-500/50 bg-rose-500/10 text-rose-200 hover:bg-rose-500/20"
        >
          − PPL1 2.0
        </button>
        <span className="px-2 py-1 rounded border border-slate-700 bg-slate-950 text-slate-400">
          KC rate {telemetry?.rates?.mushroom_body_kc ?? "—"}
        </span>
        <span className="px-2 py-1 rounded border border-slate-700 bg-slate-950 text-slate-400">
          dopamina {telemetry?.biophysics?.dopamine_level ?? "—"}
        </span>
        <span className="px-2 py-1 rounded border border-slate-700 bg-slate-950 text-slate-400">
          recompensa {telemetry?.shaped_reward ?? "—"}
        </span>
      </div>
    </div>
  );
}
