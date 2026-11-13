import React from "react";

const PALETTE = [
  "#4285f4",
  "#fbbc05",
  "#ea4335",
  "#34a853",
  "#ab47bc",
  "#26c6da",
  "#ff7043",
];

const DEFAULT_LABELS = ["TURN_LEFT", "TURN_RIGHT", "ATTACK", "IDLE"];

export default function MotorDecision({ policy }) {
  if (!policy) return null;
  const probs = policy.action_probs || [];
  const labels = policy.action_labels || DEFAULT_LABELS;
  const explRate = Number(policy.exploration_rate ?? 0);

  return (
    <div className="bg-[#252525] border border-[#383838] rounded-xl p-4 space-y-2.5 font-mono text-xs">
      <div className="flex items-center justify-between">
        <span className="text-[#448cff] uppercase">
          Política {policy.algorithm || "PPO-CNN"} ({labels.length} acciones)
        </span>
        <span
          style={{
            backgroundColor: policy.greedy
              ? "rgba(66, 133, 244, 0.15)"
              : "rgba(251, 188, 5, 0.15)",
          }}
          className={`px-2 py-0.5 rounded border text-[10px] ${
            policy.greedy
              ? "border-[#4285f4]/50 text-[#448cff]"
              : "border-[#fbbc05]/50 text-[#fbbc05]"
          }`}
        >
          {policy.greedy ? "EXPLOTACIÓN (GREEDY)" : `EXPLORACIÓN ${(explRate * 100).toFixed(0)}%`}
        </span>
      </div>

      {labels.map((label, idx) => {
        const p = probs[idx] || 0;
        const active = policy.action_idx === idx;
        const hex = PALETTE[idx % PALETTE.length];
        return (
          <div key={`${label}-${idx}`} className="space-y-1">
            <div className="flex justify-between">
              <span className={active ? "text-[#ffffff] font-bold" : "text-[#c1c1c1]"}>
                {active ? "▶ " : ""}
                {label}
              </span>
              <span className="text-[#ffffff] font-semibold">{(p * 100).toFixed(1)}%</span>
            </div>
            <div className="w-full h-2 bg-[#181818] border border-[#383838] rounded overflow-hidden">
              <div
                className="h-full transition-all duration-75"
                style={{ width: `${Math.min(100, p * 100)}%`, backgroundColor: hex }}
              />
            </div>
          </div>
        );
      })}

      <div className="flex justify-between pt-1 text-[10px] text-[#c1c1c1]">
        <span>{policy.training_enabled ? "APRENDIENDO EN VIVO" : "POLÍTICA CONGELADA"}</span>
        <span>
          EP. {policy.episodes} · KL {policy.approx_kl ?? 0}
        </span>
      </div>
    </div>
  );
}
