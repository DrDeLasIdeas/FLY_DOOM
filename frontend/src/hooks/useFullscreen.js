import { useCallback, useEffect, useState } from "react";

function isTypingTarget(target) {
  if (!target) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || target.isContentEditable;
}

export function useFullscreen(initial = false, keyboard = true) {
  const [active, setActive] = useState(() => {
    if (typeof window === "undefined") return initial;
    return new URLSearchParams(window.location.search).get("mode") === "fullscreen" || initial;
  });

  const setMode = useCallback((next) => {
    setActive(next);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      if (next) url.searchParams.set("mode", "fullscreen");
      else url.searchParams.delete("mode");
      window.history.replaceState({}, "", url);
    }
  }, []);

  const toggle = useCallback(() => setMode(!active), [active, setMode]);

  const requestBrowserFullscreen = useCallback(async () => {
    try {
      await document.documentElement.requestFullscreen?.();
    } catch (err) {
      console.warn("No se pudo activar pantalla completa del navegador:", err);
    }
  }, []);

  const exitBrowserFullscreen = useCallback(async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen?.();
    } catch (err) {
      console.warn("No se pudo salir de pantalla completa:", err);
    }
  }, []);

  useEffect(() => {
    const onKey = (event) => {
      if (isTypingTarget(event.target)) return;
      if (keyboard && (event.key === "f" || event.key === "F")) {
        event.preventDefault();
        toggle();
      }
      if (event.key === "Escape" && active) {
        setMode(false);
        exitBrowserFullscreen();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, setMode, toggle, exitBrowserFullscreen, keyboard]);

  return { active, setMode, toggle, requestBrowserFullscreen, exitBrowserFullscreen };
}
