import React, { useState } from "react";
import Navbar from "./components/Navbar.jsx";
import ConferenceDeck from "./components/ConferenceDeck.jsx";
import LiveArena from "./components/LiveArena.jsx";
import ConnectomeStudio from "./components/connectome/ConnectomeStudio.jsx";
import { useTelemetrySocket } from "./hooks/useTelemetrySocket.js";

export default function App() {
  const [mode, setMode] = useState("conference");
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

  return (
    <div className="min-h-screen bg-[#212121] text-[#ffffff] flex flex-col">
      <Navbar
        mode={mode}
        setMode={setMode}
        connected={connected}
        telemetry={telemetry}
        onSystemControl={controlSystem}
      />
      <main className="flex-1 bg-[#212121]">
        {mode === "conference" ? (
          <ConferenceDeck
            telemetry={telemetry}
            history={history}
            connected={connected}
            onDopaminePulse={sendDopaminePulse}
            onModulate={updateBiophysics}
            onTraining={sendTraining}
          />
        ) : mode === "arena" ? (
          <LiveArena
            telemetry={telemetry}
            history={history}
            onDopaminePulse={sendDopaminePulse}
            onModulate={updateBiophysics}
            onTraining={sendTraining}
            onSystemControl={controlSystem}
            onSwitchScenario={switchScenario}
            onUpdateSpeed={updateSpeed}
            onResetEpisode={resetEpisode}
            onOpenStudio={() => setMode("connectome")}
          />
        ) : (
          <ConnectomeStudio telemetry={telemetry} />
        )}
      </main>
    </div>
  );
}
