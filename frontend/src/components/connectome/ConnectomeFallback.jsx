import React, { useEffect, useRef } from "react";

export default function ConnectomeFallback({ neurons3d = [], attackPower = 0, error }) {
  const canvasRef = useRef(null);
  const angleRef = useRef(0);
  const neuronsRef = useRef(neurons3d);
  const attackRef = useRef(attackPower);

  useEffect(() => {
    neuronsRef.current = neurons3d;
  }, [neurons3d]);

  useEffect(() => {
    attackRef.current = attackPower;
  }, [attackPower]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const ctx = canvas.getContext("2d");
    let animId;

    const render = () => {
      angleRef.current += 0.008;
      const width = canvas.width;
      const height = canvas.height;
      const list = neuronsRef.current;
      const attack = attackRef.current;
      ctx.clearRect(0, 0, width, height);

      const cosA = Math.cos(angleRef.current);
      const sinA = Math.sin(angleRef.current);

      for (let i = 0; i < list.length; i += 1) {
        const neuron = list[i];
        const rx = neuron.x * cosA - neuron.z * sinA;
        const rz = neuron.x * sinA + neuron.z * cosA;
        const scale = 95 / (4.2 + rz);
        const px = width / 2 + rx * scale * 1.4;
        const py = height / 2 - neuron.y * scale * 1.4;
        const isAttackDn = neuron.id >= 19950;

        ctx.beginPath();
        if (isAttackDn && attack > 0.35) {
          ctx.fillStyle = "#fb7185";
          ctx.arc(px, py, 4.4, 0, Math.PI * 2);
        } else if (neuron.s === 1) {
          ctx.fillStyle = "#22d3ee";
          ctx.arc(px, py, 3.2, 0, Math.PI * 2);
        } else {
          ctx.fillStyle = "rgba(148, 163, 184, 0.35)";
          ctx.arc(px, py, 1.5, 0, Math.PI * 2);
        }
        ctx.fill();
      }
      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, []);

  return (
    <div className="relative w-full h-full">
      <canvas
        ref={canvasRef}
        width={520}
        height={260}
        className="w-full h-full"
        style={{ imageRendering: "auto" }}
      />
      {(error || neurons3d.length === 0) && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <span className="px-2 py-1 rounded bg-slate-950/80 border border-slate-700 font-mono text-[10px] text-slate-400">
            {error
              ? `Topología 3D no disponible (${error.message})`
              : "Cargando conectoma anatómico..."}
          </span>
        </div>
      )}
    </div>
  );
}
