import React, { useEffect, useRef, useState } from "react";
import { Eye, MousePointerClick, Sun } from "lucide-react";

const GRID = 64;

function gaussian(x, y, cx, cy, sigma) {
  const dx = x - cx;
  const dy = y - cy;
  return Math.exp(-(dx * dx + dy * dy) / (2 * sigma * sigma));
}

export default function RetinaWidget({ telemetry }) {
  const canvasRef = useRef(null);
  const [spot, setSpot] = useState({ x: 0.62, y: 0.46 });
  const [luminance, setLuminance] = useState(0.72);
  const [redBoost, setRedBoost] = useState(0.35);
  const [sigma, setSigma] = useState(0.16);
  const [dragging, setDragging] = useState(false);
  const [stats, setStats] = useState({ max: 0, active: 0, cx: 0, cy: 0 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const image = ctx.createImageData(GRID, GRID);
    const drive = (0.7 * luminance + 0.3 * redBoost) * 12;
    let max = 0;
    let active = 0;
    let sum = 0;
    let sx = 0;
    let sy = 0;
    const values = new Float32Array(GRID * GRID);

    for (let y = 0; y < GRID; y += 1) {
      for (let x = 0; x < GRID; x += 1) {
        const nx = x / (GRID - 1);
        const ny = y / (GRID - 1);
        const current = drive * gaussian(nx, ny, spot.x, spot.y, sigma);
        values[y * GRID + x] = current;
        if (current > max) max = current;
      }
    }
    const cutoff = max * 0.18;
    for (let y = 0; y < GRID; y += 1) {
      for (let x = 0; x < GRID; x += 1) {
        const current = values[y * GRID + x];
        const intensity = max > 0 ? current / max : 0;
        const index = (y * GRID + x) * 4;
        image.data[index] = Math.round(24 + 42 * intensity * luminance + 190 * intensity * redBoost);
        image.data[index + 1] = Math.round(24 + 109 * intensity * luminance);
        image.data[index + 2] = Math.round(24 + 220 * intensity * luminance);
        image.data[index + 3] = 255;
        if (current > cutoff) {
          active += 1;
          sum += current;
          sx += current * x;
          sy += current * y;
        }
      }
    }
    ctx.putImageData(image, 0, 0);
    setStats({
      max,
      active,
      cx: sum > 0 ? sx / sum / (GRID - 1) : 0,
      cy: sum > 0 ? sy / sum / (GRID - 1) : 0,
    });
  }, [spot, luminance, redBoost, sigma]);

  const updateSpot = (event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    setSpot({
      x: Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width)),
      y: Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height)),
    });
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-3">
      <div className="space-y-2">
        <div
          className="relative rounded-xl overflow-hidden border border-cyan-500/30 bg-slate-950 cursor-crosshair select-none"
          onPointerDown={(event) => {
            setDragging(true);
            event.currentTarget.setPointerCapture?.(event.pointerId);
            updateSpot(event);
          }}
          onPointerMove={(event) => {
            if (dragging) updateSpot(event);
          }}
          onPointerUp={() => setDragging(false)}
          onPointerLeave={() => setDragging(false)}
        >
          <canvas
            ref={canvasRef}
            width={GRID}
            height={GRID}
            className="w-full aspect-square"
            style={{ imageRendering: "pixelated" }}
          />
          <div
            className="absolute w-4 h-4 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/80 shadow-[0_0_12px_rgba(34,211,238,0.9)] pointer-events-none"
            style={{ left: `${spot.x * 100}%`, top: `${spot.y * 100}%` }}
          />
          <div className="absolute top-1.5 left-1.5 px-1.5 py-0.5 rounded bg-slate-950/80 border border-cyan-500/30 font-mono text-[8px] text-cyan-300">
            RETINA 64×64 · 4,096 OMATIDIOS
          </div>
          <div className="absolute bottom-1.5 right-1.5 px-1.5 py-0.5 rounded bg-slate-950/80 border border-slate-700 font-mono text-[8px] text-slate-400">
            <MousePointerClick className="inline w-2.5 h-2.5 mr-0.5" />
            clic / arrastra el estímulo
          </div>
        </div>
        <div className="grid grid-cols-3 gap-1 font-mono text-[8px] text-slate-400">
          <div className="rounded border border-slate-800 bg-slate-950 p-1.5">
            <div className="text-slate-600">I_ext máx</div>
            <div className="text-cyan-300">{stats.max.toFixed(2)} nA</div>
          </div>
          <div className="rounded border border-slate-800 bg-slate-950 p-1.5">
            <div className="text-slate-600">activos</div>
            <div className="text-emerald-300">{stats.active}</div>
          </div>
          <div className="rounded border border-slate-800 bg-slate-950 p-1.5">
            <div className="text-slate-600">centroide</div>
            <div className="text-fuchsia-300">
              {stats.cx.toFixed(2)}, {stats.cy.toFixed(2)}
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-2.5">
        <div className="grid grid-cols-2 gap-2">
          {telemetry?.frame_b64 && (
            <div className="space-y-1">
              <div className="font-mono text-[8px] text-slate-500 uppercase">Buffer ViZDoom 320×240</div>
              <img
                src={`data:image/jpeg;base64,${telemetry.frame_b64}`}
                alt="Buffer ViZDoom"
                className="w-full aspect-square object-cover rounded-lg border border-slate-700"
              />
            </div>
          )}
          {telemetry?.retina_b64 && (
            <div className="space-y-1">
              <div className="font-mono text-[8px] text-slate-500 uppercase">Retina real 64×64</div>
              <img
                src={`data:image/jpeg;base64,${telemetry.retina_b64}`}
                alt="Retina 64x64"
                className="w-full aspect-square object-cover rounded-lg border border-cyan-500/40"
                style={{ imageRendering: "pixelated" }}
              />
            </div>
          )}
        </div>

        <label className="block font-mono text-[9px] text-slate-400">
          <span className="flex items-center gap-1">
            <Sun className="w-3 h-3 text-amber-300" /> Luminancia{" "}
            <strong className="text-amber-200">{luminance.toFixed(2)}</strong>
          </span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={luminance}
            onChange={(event) => setLuminance(Number(event.target.value))}
            className="w-full accent-amber-400"
          />
        </label>
        <label className="block font-mono text-[9px] text-slate-400">
          <span className="flex items-center gap-1">
            <Eye className="w-3 h-3 text-rose-300" /> Canal rojo R7–R8{" "}
            <strong className="text-rose-200">{redBoost.toFixed(2)}</strong>
          </span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={redBoost}
            onChange={(event) => setRedBoost(Number(event.target.value))}
            className="w-full accent-rose-400"
          />
        </label>
        <label className="block font-mono text-[9px] text-slate-400">
          <span className="flex items-center justify-between">
            <span>PSF gaussiana σ</span>
            <strong className="text-cyan-200">{sigma.toFixed(2)}</strong>
          </span>
          <input
            type="range"
            min="0.05"
            max="0.4"
            step="0.01"
            value={sigma}
            onChange={(event) => setSigma(Number(event.target.value))}
            className="w-full accent-cyan-400"
          />
        </label>

        <div className="rounded-lg border border-slate-800 bg-slate-950 p-2 font-mono text-[9px] text-slate-400">
          <div className="flex justify-between">
            <span>g_sensorial</span>
            <span className="text-cyan-300">{telemetry?.biophysics?.sensory_gain ?? 18}</span>
          </div>
          <div className="flex justify-between">
            <span>R1–R6</span>
            <span className="text-slate-300">luminancia</span>
          </div>
          <div className="flex justify-between">
            <span>R7–R8</span>
            <span className="text-rose-300">rojo / amenaza</span>
          </div>
        </div>
      </div>
    </div>
  );
}
