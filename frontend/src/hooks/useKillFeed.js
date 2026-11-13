import { useEffect, useRef, useState } from "react";

export function useKillFeed(telemetry, limit = 8) {
  const lastKills = useRef(null);
  const [events, setEvents] = useState([]);
  const [flash, setFlash] = useState(false);

  useEffect(() => {
    const total = telemetry?.total_kills ?? 0;
    if (lastKills.current === null) {
      lastKills.current = total;
      return undefined;
    }
    if (total > lastKills.current) {
      const delta = total - lastKills.current;
      const time = new Date().toLocaleTimeString([], { hour12: false });
      const fresh = Array.from({ length: delta }, (_, i) => ({
        id: `${Date.now()}-${i}`,
        totalKills: total - delta + i + 1,
        episode: telemetry?.episode ?? 0,
        time,
      }));
      setEvents((prev) => [...fresh.reverse(), ...prev].slice(0, limit));
      setFlash(true);
      lastKills.current = total;
      const timer = setTimeout(() => setFlash(false), 1400);
      return () => clearTimeout(timer);
    }
    lastKills.current = total;
    return undefined;
  }, [telemetry?.total_kills, telemetry?.episode, limit]);

  return { events, flash };
}
