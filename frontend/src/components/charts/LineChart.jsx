import React from "react";

export default function LineChart({
  values = [],
  color = "#fb7185",
  height = 64,
  fill = true,
  min: fixedMin,
  max: fixedMax,
  placeholder = "Esperando datos...",
}) {
  if (!values || values.length < 2) {
    return (
      <div
        className="flex items-center justify-center text-[10px] text-slate-500 font-mono border border-dashed border-slate-800 rounded-lg"
        style={{ height }}
      >
        {placeholder}
      </div>
    );
  }

  const w = 300;
  const h = height;
  const pad = 4;
  const lo = fixedMin ?? Math.min(...values);
  const hi = fixedMax ?? Math.max(...values);
  const span = hi - lo || 1;
  const pts = values
    .map((v, i) => {
      const x = pad + (i / (values.length - 1)) * (w - pad * 2);
      const y = h - pad - ((v - lo) / span) * (h - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ height }}>
        {fill && (
          <polygon
            points={`${pad},${h - pad} ${pts} ${w - pad},${h - pad}`}
            fill={color}
            fillOpacity="0.12"
          />
        )}
        <polyline points={pts} fill="none" stroke={color} strokeWidth="1.6" />
      </svg>
      <span className="absolute top-0 right-1 text-[9px] font-mono text-slate-500">
        {hi.toFixed(1)}
      </span>
      <span className="absolute bottom-0 right-1 text-[9px] font-mono text-slate-500">
        {lo.toFixed(1)}
      </span>
    </div>
  );
}
