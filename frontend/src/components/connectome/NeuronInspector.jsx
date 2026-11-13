import React from "react";
import { Crosshair, MousePointer2, Pin, X } from "lucide-react";
import { REGION_HEX } from "./palette.js";

const REGION_ROLES = {
  0: "Fotorreceptor R1–R8 del ojo izquierdo: capta luminancia y color rojo de amenazas en el hemicampo izquierdo.",
  1: "Fotorreceptor R1–R8 del ojo derecho: capta luminancia y color rojo de amenazas en el hemicampo derecho.",
  2: "Neurona T4/T5 de médula óptica izquierda: detecta bordes y movimiento visual local hacia la izquierda.",
  3: "Neurona T4/T5 de médula óptica derecha: detecta bordes y movimiento visual local hacia la derecha.",
  4: "Célula de Kenyon (KC): codifica patrones visuales dispersos y forma memoria asociativa con dopamina.",
  5: "Neurona del Complejo Central: integra orientación espacial, rumbo de la mosca y centrado del objetivo.",
  6: "Neurona de salida MBON: evalúa la valencia aprendida (acercarse o evadir) hacia las vías motoras.",
  7: "Neurona dopaminérgica PAM/PPL1: emite la señal de recompensa o castigo que modula la plasticidad R-STDP.",
  8: "Neurona descendente motora DNp20_L: ordena al tórax girar hacia la izquierda para alinear la amenaza.",
  9: "Neurona descendente motora DNp20_R: ordena al tórax girar hacia la derecha para alinear la amenaza.",
  10: "Neurona descendente locomotora DN_move: coordina el avance y estabilización postural en la arena.",
  11: "Neurona descendente de ataque DNp09: dispara la respuesta ofensiva cuando el enemigo está fijado.",
};

function getNeuronDescription(info) {
  if (!info) return "";
  return (
    REGION_ROLES[info.region] ??
    "Interneurona del conectoma FlyWire: integra corrientes sinápticas LIF y propaga pulsos hacia regiones motoras."
  );
}

function Row({ label, value, tone = "text-slate-200" }) {
  return (
    <div className="flex items-center justify-between gap-2 font-mono text-[10px]">
      <span className="text-slate-500">{label}</span>
      <span className={`${tone} truncate`}>{value}</span>
    </div>
  );
}

export default function NeuronInspector({ info, pinned = false, onClear }) {
  if (!info) {
    return (
      <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/60 p-3">
        <div className="flex items-center gap-2 text-[11px] text-slate-400">
          <MousePointer2 className="w-4 h-4 text-cyan-400" />
          Pasa el cursor sobre una neurona dinámica y haz clic para fijarla.
        </div>
        <div className="mt-2 grid grid-cols-2 gap-1 font-mono text-[9px] text-slate-600">
          <span>hover → lectura</span>
          <span>click → fijar</span>
          <span>espiga → edad</span>
          <span>V → mV reales</span>
        </div>
      </div>
    );
  }

  const color = REGION_HEX[info.region] ?? "#94a3b8";
  const description = getNeuronDescription(info);
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-950/80 p-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
            style={{ backgroundColor: color, boxShadow: `0 0 8px ${color}` }}
          />
          <div className="min-w-0">
            <div className="text-[11px] font-semibold text-white truncate">{info.regionName}</div>
            <div className="text-[9px] font-mono text-slate-500">
              FlyWire ID {info.globalIndex} · local {info.index}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {pinned ? (
            <span className="flex items-center gap-1 px-1.5 py-0.5 rounded border border-cyan-500/40 text-[8px] font-mono text-cyan-300">
              <Pin className="w-2.5 h-2.5" /> FIJA
            </span>
          ) : (
            <span className="px-1.5 py-0.5 rounded border border-slate-700 text-[8px] font-mono text-slate-400">
              HOVER
            </span>
          )}
          {pinned && onClear && (
            <button
              onClick={onClear}
              className="p-1 rounded border border-slate-700 text-slate-400 hover:text-rose-300 hover:border-rose-500/50"
              title="Limpiar selección"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      <p className="text-[10px] leading-snug text-slate-300 bg-slate-900/90 border border-slate-800 rounded-lg px-2.5 py-1.5 line-clamp-2">
        {description}
      </p>

      <div className="grid grid-cols-2 gap-x-3 gap-y-1">
        <Row
          label="V membrana"
          value={`${info.voltage.toFixed(2)} mV`}
          tone={info.voltage >= -46 ? "text-amber-300" : "text-cyan-300"}
        />
        <Row
          label="Última espiga"
          value={info.age == null ? "—" : `${info.age.toFixed(2)} s`}
          tone={info.age == null ? "text-slate-500" : "text-fuchsia-300"}
        />
        <Row label="x" value={info.x.toFixed(2)} />
        <Row label="y" value={info.y.toFixed(2)} />
        <Row label="z" value={info.z.toFixed(2)} />
        <Row label="canal" value={`R${info.region + 1}`} tone="text-slate-400" />
      </div>

      <div className="flex items-center gap-1 text-[9px] font-mono text-slate-500 pt-1 border-t border-slate-800">
        <Crosshair className="w-3 h-3 text-cyan-400" />
        Voltaje reconstruido de uint8 normalizado con V_rest/V_th.
      </div>
    </div>
  );
}
