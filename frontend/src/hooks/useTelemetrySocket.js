import { useEffect, useRef, useState, useCallback } from "react";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://127.0.0.1:8000/ws/telemetry";
const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export function useTelemetrySocket() {
  const [telemetry, setTelemetry] = useState(null);
  const [connected, setConnected] = useState(false);
  const [history, setHistory] = useState([]);
  const wsRef = useRef(null);

  useEffect(() => {
    let isMounted = true;
    let reconnectTimer = null;

    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (isMounted) setConnected(true);
      };

      ws.onmessage = (event) => {
        if (!isMounted) return;
        const data = JSON.parse(event.data);
        setTelemetry(data);
        setHistory((prev) => [...prev.slice(-59), data.rates]);
      };

      ws.onclose = (event) => {
        if (!isMounted) return;
        setConnected(false);
        // 4000 = otra pestaña tomó la sesión de telemetría; no pelear por el socket.
        if (event.code === 4000) return;
        reconnectTimer = setTimeout(connect, 1500);
      };
    }

    connect();
    return () => {
      isMounted = false;
      clearTimeout(reconnectTimer);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const sendDopaminePulse = useCallback(async (valence) => {
    try {
      await fetch(`${API_URL}/api/dopamine-pulse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ valence }),
      });
    } catch (err) {
      console.error("Error enviando pulso de dopamina:", err);
    }
  }, []);

  const updateBiophysics = useCallback(async (params) => {
    try {
      await fetch(`${API_URL}/api/modulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      });
    } catch (err) {
      console.error("Error modulando biofísica:", err);
    }
  }, []);

  const sendTraining = useCallback(async (payload) => {
    try {
      const res = await fetch(`${API_URL}/api/training`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      return await res.json();
    } catch (err) {
      console.error("Error controlando el entrenamiento:", err);
      return null;
    }
  }, []);

  const controlSystem = useCallback(async (payload) => {
    try {
      const res = await fetch(`${API_URL}/api/system`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      setTelemetry((prev) =>
        prev
          ? {
              ...prev,
              system_running: data.system_running ?? prev.system_running,
              last_saved_at: data.last_saved_at ?? prev.last_saved_at,
              total_kills: data.total_kills ?? prev.total_kills,
              policy: prev.policy
                ? {
                    ...prev.policy,
                    system_running: data.system_running ?? prev.policy.system_running,
                    last_saved_at: data.last_saved_at ?? prev.policy.last_saved_at,
                    total_kills: data.total_kills ?? prev.policy.total_kills,
                    episodes: data.episodes ?? prev.policy.episodes,
                  }
                : prev.policy,
            }
          : prev
      );
      return data;
    } catch (err) {
      console.error("Error controlando el sistema:", err);
      return null;
    }
  }, []);

  const switchScenario = useCallback(async (scenarioId, skill = null) => {
    try {
      const res = await fetch(`${API_URL}/api/scenario`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario_id: scenarioId, skill }),
      });
      return await res.json();
    } catch (err) {
      console.error("Error cambiando de escenario:", err);
      return null;
    }
  }, []);

  const updateSpeed = useCallback(async (payload) => {
    try {
      const res = await fetch(`${API_URL}/api/speed`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      return await res.json();
    } catch (err) {
      console.error("Error ajustando velocidad de simulación:", err);
      return null;
    }
  }, []);

  const resetEpisode = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/episode/reset`, {
        method: "POST",
      });
      return await res.json();
    } catch (err) {
      console.error("Error reiniciando episodio:", err);
      return null;
    }
  }, []);

  return {
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
  };
}
