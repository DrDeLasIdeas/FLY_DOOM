import { useEffect, useState } from "react";
import { decodeTopology } from "./decodeTelemetry.js";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

let cachedTopology = null;
let inflight = null;

function loadTopology() {
  if (cachedTopology) return Promise.resolve(cachedTopology);
  if (!inflight) {
    inflight = fetch(`${API_URL}/api/connectome/topology`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((asset) => {
        cachedTopology = decodeTopology(asset);
        return cachedTopology;
      })
      .catch((err) => {
        inflight = null;
        throw err;
      });
  }
  return inflight;
}

export function useTopology() {
  const [topology, setTopology] = useState(cachedTopology);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    loadTopology()
      .then((asset) => {
        if (active) setTopology(asset);
      })
      .catch((err) => {
        if (active) setError(err);
      });
    return () => {
      active = false;
    };
  }, []);

  return { topology, error };
}
