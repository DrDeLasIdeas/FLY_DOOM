import React, { useCallback, useState } from "react";
import Navbar from "./components/Navbar.jsx";
import ConferenceDeck from "./components/ConferenceDeck.jsx";
import LiveArena from "./components/LiveArena.jsx";
import FullscreenArena from "./components/FullscreenArena.jsx";
import ConnectomeStudio from "./components/connectome/ConnectomeStudio.jsx";
import { useTelemetrySocket } from "./hooks/useTelemetrySocket.js";
import { useRetroAudio } from "./hooks/useRetroAudio.js";

function getInitialMode() {
  if (typeof window === "undefined") return "conference";
  const param = new URLSearchParams(window.location.search).get("mode");
  if (param && ["conference", "arena", "connectome", "fullscreen"].includes(param)) {
    return param;
  }
  return "conference";
}

export default function App() {
  const [mode, setMode] = useState(getInitialMode);
  const {
    telemetry,
    history,
    connected,
    sendDopaminePulse,
    updateBiophysics,
    sendTraining,
    controlSystem,
    switchScenario,
    updateSpeed,
    resetEpisode,
  } = useTelemetrySocket();

  const {
    audioEnabled,
    musicEnabled,
    sfxEnabled,
    toggleAudio,
    toggleMusic,
    toggleSfx,
    triggerDopamineSfx,
  } = useRetroAudio(telemetry);

  const handleDopaminePulse = useCallback(
    (valence) => {
      triggerDopamineSfx(valence);
      return sendDopaminePulse(valence);
    },
    [sendDopaminePulse, triggerDopamineSfx]
  );

  const requestBrowserFullscreen = useCallback(async () => {
    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen?.();
      } else {
        await document.exitFullscreen?.();
      }
    } catch {
      // ignore fullscreen permission rejections
    }
  }, []);

  return (
    <div className="min-h-screen bg-[#212121] text-[#ffffff] flex flex-col">
      <Navbar
        mode={mode}
        setMode={setMode}
        connected={connected}
        telemetry={telemetry}
        onSystemControl={controlSystem}
        audioEnabled={audioEnabled}
        musicEnabled={musicEnabled}
        sfxEnabled={sfxEnabled}
        onToggleAudio={toggleAudio}
        onToggleMusic={toggleMusic}
        onToggleSfx={toggleSfx}
      />
      <main className="flex-1 bg-[#212121]">
        {mode === "conference" ? (
          <ConferenceDeck
            telemetry={telemetry}
            history={history}
            connected={connected}
            onDopaminePulse={handleDopaminePulse}
            onModulate={updateBiophysics}
            onTraining={sendTraining}
          />
        ) : mode === "arena" ? (
          <LiveArena
            telemetry={telemetry}
            history={history}
            onDopaminePulse={handleDopaminePulse}
            onModulate={updateBiophysics}
            onTraining={sendTraining}
            onSystemControl={controlSystem}
            onSwitchScenario={switchScenario}
            onUpdateSpeed={updateSpeed}
            onResetEpisode={resetEpisode}
            onOpenStudio={() => setMode("connectome")}
          />
        ) : mode === "fullscreen" ? (
          <FullscreenArena
            telemetry={telemetry}
            history={history}
            onTraining={sendTraining}
            onSystemControl={controlSystem}
            onSwitchScenario={switchScenario}
            audioEnabled={audioEnabled}
            musicEnabled={musicEnabled}
            sfxEnabled={sfxEnabled}
            onToggleAudio={toggleAudio}
            onToggleMusic={toggleMusic}
            onToggleSfx={toggleSfx}
            onExit={() => setMode("arena")}
            onRequestBrowserFullscreen={requestBrowserFullscreen}
          />
        ) : (
          <ConnectomeStudio telemetry={telemetry} />
        )}
      </main>
    </div>
  );
}
