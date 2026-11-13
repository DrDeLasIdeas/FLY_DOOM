import React from "react";
import { Sparkles, ThumbsUp, ThumbsDown, Sliders } from "lucide-react";

export default function GemmaBrainConsole({
  gemma,
  biophysics,
  onDopaminePulse,
  onModulate,
}) {
  if (!gemma || !biophysics) return null;

  return (
    <div className="bg-[#252525] border border-[#383838] rounded-xl p-4 space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono uppercase tracking-wider text-[#34a853] flex items-center gap-1.5">
          <Sparkles className="w-4 h-4" /> Sistema 2: Neuromodulador Gemma 3
        </span>
        <span
          style={{ backgroundColor: "rgba(52, 168, 83, 0.15)" }}
          className="text-[11px] font-mono px-2 py-0.5 rounded text-[#34a853] border border-[#34a853]/45"
        >
          {gemma.status}
        </span>
      </div>

      <div className="p-3.5 rounded-xl bg-[#181818] border border-[#383838] text-xs font-mono text-[#ffffff] leading-relaxed">
        <div className="text-[10px] text-[#c1c1c1] mb-1">
          HIPÓTESIS NEUROQUÍMICA ({gemma.model}):
        </div>
        "{gemma.neuro_hypothesis}"
      </div>

      <div className="space-y-2 pt-1">
        <div className="text-xs font-semibold text-[#ffffff] flex items-center gap-1.5">
          <Sliders className="w-3.5 h-3.5 text-[#4285f4]" /> Intervención Neuroquímica en Vivo
        </div>

        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => onDopaminePulse(2.0)}
            style={{ backgroundColor: "rgba(52, 168, 83, 0.15)" }}
            className="flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl hover:brightness-110 border border-[#34a853]/50 text-[#34a853] text-xs font-semibold transition"
          >
            <ThumbsUp className="w-3.5 h-3.5" /> +Pulso PAM (+Premio)
          </button>
          <button
            onClick={() => onDopaminePulse(-2.0)}
            style={{ backgroundColor: "rgba(234, 67, 53, 0.15)" }}
            className="flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl hover:brightness-110 border border-[#ea4335]/50 text-[#ea4335] text-xs font-semibold transition"
          >
            <ThumbsDown className="w-3.5 h-3.5" /> -Pulso PPL1 (-Castigo)
          </button>
        </div>

        <div className="pt-2 space-y-2 text-xs font-mono">
          <label className="flex justify-between text-[#c1c1c1]">
            <span>Umbral de Disparo (V_th):</span>
            <span className="text-[#fbbc05] font-semibold">{biophysics.v_thresh} mV</span>
          </label>
          <input
            type="range"
            min="-48.5"
            max="-41.5"
            step="0.25"
            value={biophysics.v_thresh}
            onChange={(e) => onModulate({ v_thresh: parseFloat(e.target.value) })}
            style={{ accentColor: "#fbbc05" }}
            className="w-full"
          />

          <label className="flex justify-between text-[#c1c1c1]">
            <span>Ganancia Sensorial Retinotópica:</span>
            <span className="text-[#448cff] font-semibold">{biophysics.sensory_gain}</span>
          </label>
          <input
            type="range"
            min="8"
            max="30"
            step="1"
            value={biophysics.sensory_gain}
            onChange={(e) => onModulate({ sensory_gain: parseFloat(e.target.value) })}
            style={{ accentColor: "#4285f4" }}
            className="w-full"
          />
        </div>
      </div>
    </div>
  );
}
