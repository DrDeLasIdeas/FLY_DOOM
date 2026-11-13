import React, { useMemo } from "react";
import katex from "katex";
import "katex/dist/katex.min.css";

export default function Equation({ tex, block = true, label, className = "" }) {
  const html = useMemo(
    () =>
      katex.renderToString(tex, {
        displayMode: block,
        throwOnError: false,
        strict: "ignore",
        output: "html",
      }),
    [tex, block],
  );

  return (
    <div
      className={`rounded-xl border border-cyan-500/20 bg-slate-950/90 px-4 py-3 overflow-x-auto ${
        block ? "text-center" : ""
      } ${className}`}
    >
      {label && (
        <div className="text-[9px] font-mono uppercase tracking-wider text-slate-500 mb-1 text-left">
          {label}
        </div>
      )}
      <div
        className="text-cyan-100 [&_.katex]:text-[1.02em]"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}
