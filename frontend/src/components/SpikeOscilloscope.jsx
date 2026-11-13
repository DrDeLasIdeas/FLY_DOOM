import React from "react";

const REGIONS = [
  { key: "retina_r1_r8", label: "Retina (R1-R8)", hex: "#4285f4" },
  { key: "optic_lobe_t4_t5", label: "Lóbulo Óptico (T4/T5)", hex: "#448cff" },
  { key: "mushroom_body_kc", label: "Mushroom Body (KC)", hex: "#fbbc05" },
  { key: "mbon_valence", label: "Salida MBON (Valencia)", hex: "#34a853" },
  { key: "dan_dopamine", label: "Clusters Dopamina (PAM/PPL1)", hex: "#34a853" },
  { key: "dn_attack", label: "DNp09 (Ataque / Shotgun Trigger)", hex: "#ea4335" },
];

export default function SpikeOscilloscope({ rates = {}, history = [] }) {
  return (
    <div className="bg-[#252525] border border-[#383838] rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono uppercase tracking-wider text-[#448cff]">
          Osciloscopio de Tasas de Disparo por Población Neuropilar
        </span>
        <span className="text-[11px] font-mono text-[#c1c1c1]">
          Ventana: {history.length} frames
        </span>
      </div>

      <div className="space-y-2.5">
        {REGIONS.map((reg) => {
          const val = rates[reg.key] || 0;
          const pct = Math.min(100, Math.round(val * 450));
          return (
            <div key={reg.key} className="space-y-1">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-[#c1c1c1] flex items-center gap-1.5">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: reg.hex }}
                  />
                  {reg.label}
                </span>
                <span className="text-[#ffffff] font-semibold">{(val * 100).toFixed(2)}%</span>
              </div>
              <div className="w-full h-2 bg-[#181818] rounded-full overflow-hidden border border-[#383838]">
                <div
                  className="h-full transition-all duration-75"
                  style={{ width: `${pct}%`, backgroundColor: reg.hex }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
