import React, { useEffect, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
  Minus,
  NotebookPen,
  Plus,
  Radio,
  Sparkles,
  Type,
  X,
} from "lucide-react";
import { SLIDES } from "./deck/Slides.jsx";

const ACCENTS = {
  cyan: "text-[#448cff] border-[#4285f4]/50 bg-[#4285f4]/15",
  emerald: "text-[#34a853] border-[#34a853]/50 bg-[#34a853]/15",
  violet: "text-[#fbbc05] border-[#fbbc05]/50 bg-[#fbbc05]/15",
  fuchsia: "text-[#448cff] border-[#4285f4]/50 bg-[#4285f4]/15",
  amber: "text-[#ea4335] border-[#ea4335]/50 bg-[#ea4335]/15",
};

const MIN_FONT_SCALE = 0.85;
const MAX_FONT_SCALE = 1.65;
const DEFAULT_FONT_SCALE = 1.15;

export default function ConferenceDeck({
  telemetry,
  connected,
  onDopaminePulse,
}) {
  const [activeStage, setActiveStage] = useState(0);
  const [presenting, setPresenting] = useState(false);
  const [showNotes, setShowNotes] = useState(false);
  const [fontScale, setFontScale] = useState(() => {
    try {
      const saved = Number(localStorage.getItem("neurodoom_deck_font_scale"));
      if (Number.isFinite(saved) && saved >= MIN_FONT_SCALE && saved <= MAX_FONT_SCALE) {
        return saved;
      }
    } catch {
      // ignore storage errors
    }
    return DEFAULT_FONT_SCALE;
  });

  const adjustFontScale = (delta) => {
    setFontScale((prev) => {
      const next = Math.round(Math.min(MAX_FONT_SCALE, Math.max(MIN_FONT_SCALE, prev + delta)) * 100) / 100;
      try {
        localStorage.setItem("neurodoom_deck_font_scale", String(next));
      } catch {
        // ignore storage errors
      }
      return next;
    });
  };

  const resetFontScale = () => {
    setFontScale(DEFAULT_FONT_SCALE);
    try {
      localStorage.setItem("neurodoom_deck_font_scale", String(DEFAULT_FONT_SCALE));
    } catch {
      // ignore storage errors
    }
  };

  const current = SLIDES[activeStage];
  const Icon = current.icon;
  const Slide = current.Component;
  const accent = ACCENTS[current.accent] ?? ACCENTS.cyan;
  const isLast = activeStage === SLIDES.length - 1;
  const isFirst = activeStage === 0;

  const enterBrowserFullscreen = async () => {
    try {
      await document.documentElement.requestFullscreen?.();
    } catch (err) {
      console.warn("No se pudo activar pantalla completa:", err);
    }
  };

  useEffect(() => {
    const onKey = (event) => {
      const tag = event.target?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || event.target?.isContentEditable) return;
      if (event.key === "ArrowRight" || event.key === "PageDown") {
        event.preventDefault();
        setActiveStage((previous) => Math.min(SLIDES.length - 1, previous + 1));
      }
      if (event.key === "ArrowLeft" || event.key === "PageUp") {
        event.preventDefault();
        setActiveStage((previous) => Math.max(0, previous - 1));
      }
      if (event.key >= "1" && event.key <= "5") {
        setActiveStage(Number(event.key) - 1);
      }
      if (event.key === "+" || event.key === "=") {
        event.preventDefault();
        adjustFontScale(0.1);
      }
      if (event.key === "-" || event.key === "_") {
        event.preventDefault();
        adjustFontScale(-0.1);
      }
      if (event.key === "f" || event.key === "F") {
        event.preventDefault();
        enterBrowserFullscreen();
      }
      if (event.key === "n" || event.key === "N") {
        setShowNotes((previous) => !previous);
      }
      if (event.key === "Escape" && presenting) {
        setPresenting(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [presenting]);

  return (
    <div
      className={
        presenting
          ? "fixed inset-0 z-50 bg-slate-950 overflow-y-auto"
          : "w-full max-w-[1720px] mx-auto p-4 sm:p-6 lg:p-8"
      }
    >
      <div className={presenting ? "min-h-screen p-4 sm:p-6 lg:p-10 flex flex-col gap-5" : "space-y-5"}>
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div className={`p-3 rounded-xl border ${accent}`}>
              <Sparkles className="w-7 h-7" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-mono uppercase tracking-[0.2em] text-cyan-400">
                  NEURODOOM OS · CONFERENCIA TÉCNICA
                </span>
                <span
                  className={`flex items-center gap-1 px-2.5 py-0.5 rounded-full border font-mono text-[11px] ${
                    connected
                      ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                      : "border-rose-500/40 bg-rose-500/10 text-rose-300"
                  }`}
                >
                  <Radio className="w-3 h-3" />
                  {connected ? "STREAM 35 Hz" : "SIN STREAM"}
                </span>
              </div>
              <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-white tracking-tight">
                Del ojo compuesto al conectoma: 5 etapas de una SNN biológica
              </h1>
              <p className="text-xs sm:text-sm text-slate-400">
                FlyWire v783 · LIF disperso · R-STDP · Gemma 3 local · Apple Silicon ARM64
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div
              className="flex items-center gap-1 rounded-xl border border-slate-700 bg-slate-900/90 p-1"
              title="Ajustar tamaño de letra para pantalla de escenario (+ / -)"
            >
              <span className="flex items-center gap-1 px-2 text-[11px] font-mono text-slate-400">
                <Type className="w-3.5 h-3.5 text-cyan-400" />
                Letra
              </span>
              <button
                type="button"
                onClick={() => adjustFontScale(-0.1)}
                disabled={fontScale <= MIN_FONT_SCALE}
                className="flex items-center gap-0.5 px-2.5 py-1 rounded-lg border border-slate-700 bg-slate-950 text-xs font-mono font-bold text-slate-200 hover:border-cyan-500/60 hover:text-cyan-300 disabled:opacity-30 transition"
                title="Reducir tamaño de letra (-)"
              >
                A<Minus className="w-3 h-3" />
              </button>
              <button
                type="button"
                onClick={resetFontScale}
                className="px-2 py-1 rounded-lg text-xs font-mono text-cyan-300 hover:bg-slate-800 transition"
                title="Restablecer tamaño de letra"
              >
                {Math.round(fontScale * 100)}%
              </button>
              <button
                type="button"
                onClick={() => adjustFontScale(0.1)}
                disabled={fontScale >= MAX_FONT_SCALE}
                className="flex items-center gap-0.5 px-2.5 py-1 rounded-lg border border-cyan-500/50 bg-cyan-500/15 text-xs font-mono font-bold text-cyan-200 hover:bg-cyan-500/25 disabled:opacity-30 transition"
                title="Aumentar tamaño de letra (+)"
              >
                A<Plus className="w-3 h-3" />
              </button>
            </div>

            <button
              onClick={() => setShowNotes((previous) => !previous)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg border text-xs font-mono uppercase tracking-wide transition ${
                showNotes
                  ? "border-amber-500/60 bg-amber-500/10 text-amber-200"
                  : "border-slate-700 text-slate-300 hover:border-slate-500"
              }`}
            >
              <NotebookPen className="w-4 h-4" />
              Notas
            </button>
            <button
              onClick={enterBrowserFullscreen}
              className="p-2 rounded-lg border border-slate-700 text-slate-300 hover:text-cyan-300 hover:border-cyan-500/50"
              title="Pantalla completa del navegador (F)"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPresenting((previous) => !previous)}
              className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg border text-xs font-mono uppercase tracking-wide transition ${
                presenting
                  ? "border-rose-500/60 bg-rose-500/10 text-rose-200"
                  : "border-cyan-500/60 bg-cyan-500/10 text-cyan-200"
              }`}
            >
              {presenting ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              {presenting ? "Salir" : "Presentar"}
            </button>
          </div>
        </header>

        <nav className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
          {SLIDES.map((slide, index) => {
            const StageIcon = slide.icon;
            const stageAccent = ACCENTS[slide.accent] ?? ACCENTS.cyan;
            const active = index === activeStage;
            return (
              <button
                key={slide.id}
                onClick={() => setActiveStage(index)}
                className={`text-left p-3 rounded-xl border transition ${
                  active
                    ? `${stageAccent} shadow-lg`
                    : "bg-slate-900/70 border-slate-800 text-slate-400 hover:border-slate-600"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 font-mono text-xs uppercase tracking-wider">
                    <StageIcon className="w-4 h-4" />
                    Etapa 0{slide.id}
                  </span>
                  {active && <span className="w-2 h-2 rounded-full bg-current animate-pulse" />}
                </div>
                <div className="mt-1 text-sm sm:text-base font-semibold leading-tight">{slide.short}</div>
                <div className="mt-2 h-1 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-current transition-[width] duration-300"
                    style={{ width: active ? "100%" : "0%" }}
                  />
                </div>
              </button>
            );
          })}
        </nav>

        <main
          className="flex-1 rounded-2xl border border-slate-800 bg-slate-900/90 p-5 sm:p-6 lg:p-8 space-y-5 transition-all"
          style={{ zoom: fontScale }}
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className={`p-2.5 rounded-xl border ${accent}`}>
                <Icon className="w-6 h-6" />
              </div>
              <div>
                <div className="font-mono text-xs uppercase tracking-[0.18em] text-slate-400">
                  {current.badge}
                </div>
                <h2 className="text-xl sm:text-2xl lg:text-3xl font-bold text-white">{current.title}</h2>
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setActiveStage((previous) => Math.max(0, previous - 1))}
                disabled={isFirst}
                className="p-2 rounded-lg border border-slate-700 text-slate-300 hover:border-slate-500 disabled:opacity-30"
                title="Anterior (←)"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <span className="font-mono text-xs text-slate-400 px-1.5">
                {activeStage + 1} / {SLIDES.length}
              </span>
              <button
                onClick={() => setActiveStage((previous) => Math.min(SLIDES.length - 1, previous + 1))}
                disabled={isLast}
                className="p-2 rounded-lg border border-cyan-500/60 bg-cyan-500/10 text-cyan-200 hover:bg-cyan-500/20 disabled:opacity-30"
                title="Siguiente (→)"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>

          <Slide
            telemetry={telemetry}
            presenting={presenting}
            onDopaminePulse={onDopaminePulse}
          />

          <div className="flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-slate-800">
            <div className="flex items-center gap-2 font-mono text-xs text-slate-400">
              <button
                onClick={() => setActiveStage((previous) => Math.max(0, previous - 1))}
                disabled={isFirst}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-700 hover:border-slate-500 disabled:opacity-30"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Anterior
              </button>
              <button
                onClick={() => setActiveStage((previous) => Math.min(SLIDES.length - 1, previous + 1))}
                disabled={isLast}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-cyan-500/50 text-cyan-200 hover:bg-cyan-500/10 disabled:opacity-30"
              >
                Siguiente <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="font-mono text-xs text-slate-500">
              ← → cambiar · 1–5 saltar · A+/A- tamaño letra · N notas · F pantalla completa
            </div>
          </div>
        </main>

        {showNotes && (
          <section
            className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,0.7fr)] gap-4"
            style={{ zoom: fontScale }}
          >
            <div className="rounded-2xl border border-amber-500/30 bg-amber-950/10 p-5 space-y-2.5">
              <div className="flex items-center gap-1.5 font-mono text-xs uppercase tracking-wider text-amber-300">
                <NotebookPen className="w-4 h-4" /> Notas del ponente · Etapa 0{current.id}
              </div>
              <ul className="space-y-2 text-sm text-amber-100/90">
                {current.notes.map((note) => (
                  <li key={note} className="flex gap-2.5">
                    <span className="mt-2 w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                    <span className="leading-relaxed">{note}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 space-y-2.5">
              <div className="flex items-center gap-1.5 font-mono text-xs uppercase tracking-wider text-slate-400">
                <BookOpen className="w-4 h-4 text-cyan-400" /> Referencias
              </div>
              <ol className="space-y-2 text-xs sm:text-sm text-slate-300 list-decimal list-inside">
                {current.refs.map((ref) => (
                  <li key={ref} className="leading-relaxed">
                    {ref}
                  </li>
                ))}
              </ol>
            </div>
          </section>
        )}

        {presenting && (
          <button
            onClick={() => setPresenting(false)}
            className="fixed top-3 right-3 z-[60] p-2.5 rounded-full border border-rose-500/50 bg-slate-950/90 text-rose-300 hover:bg-rose-500/20"
            title="Salir del modo presentación (Esc)"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>
    </div>
  );
}
