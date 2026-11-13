"""ConnectomeTelemetrySerializer — SRP module for 3D topology & bitfield serialization."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any

import numpy as np

from .config import settings
from .connectome_geometry import build_region_meshes

if TYPE_CHECKING:
    from .connectome_snn import DrosophilaConnectomeEngine


class ConnectomeTelemetrySerializer:
    """Serializes biophysical SNN state into compact WebSocket/REST payloads."""

    def __init__(self, engine: "DrosophilaConnectomeEngine"):
        self._engine = engine
        self._topology_asset: dict[str, Any] | None = None
        self._activity_seq: int = 0

    @staticmethod
    def encode_bytes(array: np.ndarray) -> str:
        return base64.b64encode(np.ascontiguousarray(array).tobytes()).decode("ascii")

    def _build_region_meshes(self) -> list[dict[str, Any]]:
        try:
            meshes = build_region_meshes(self._engine.region_names)
        except Exception:
            return []

        return [
            {
                "group": int(mesh["group"]),
                "name": mesh["name"],
                "vertices_b64": self.encode_bytes(mesh["vertices"]),
                "faces_b64": self.encode_bytes(mesh["faces"]),
                "centroid": [round(float(value), 4) for value in mesh["centroid"]],
            }
            for mesh in meshes
        ]

    def get_topology_asset(self) -> dict[str, Any]:
        eng = self._engine
        if self._topology_asset is None:
            self._topology_asset = {
                "num_neurons": eng.N,
                "num_visible": int(len(eng.visible_idx)),
                "num_ghost": int(len(eng.ghost_idx)),
                "positions_b64": self.encode_bytes(eng.visible_positions),
                "regions_b64": self.encode_bytes(eng.visible_regions),
                "ghost_positions_b64": self.encode_bytes(eng.ghost_positions),
                "ghost_regions_b64": self.encode_bytes(eng.ghost_regions),
                "visible_idx_b64": self.encode_bytes(eng.visible_idx.astype(np.int32)),
                "edges_b64": self.encode_bytes(eng.display_edges_local),
                "edge_sign_b64": self.encode_bytes(eng.edge_sign),
                "edge_weight_b64": self.encode_bytes(eng.edge_weight),
                "region_names": eng.region_names,
                "region_counts": eng.region_counts,
                "synapse_stats": {
                    **eng.synapse_stats,
                    "visible_display": int(len(eng.display_edges_local)),
                },
                "biophysics": {
                    "v_rest": eng.v_rest,
                    "v_thresh": eng.v_thresh,
                    "v_reset": eng.v_reset,
                    "tau_m": eng.tau_m,
                    "tau_syn": eng.tau_syn,
                    "substeps_per_frame": settings.substeps_per_frame,
                    "device": str(eng.device),
                },
                "meshes": self._build_region_meshes(),
                "dtype": {
                    "positions": "float32",
                    "regions": "uint8",
                    "ghost_positions": "float32",
                    "ghost_regions": "uint8",
                    "visible_idx": "int32",
                    "edges": "int32",
                    "mesh_faces": "uint32",
                },
            }
        return self._topology_asset

    def get_dynamic_activity(self) -> dict[str, Any]:
        eng = self._engine
        spikes = eng.spikes[eng._visible_idx_t].detach().cpu().numpy()
        voltages = eng.v[eng._visible_idx_t].detach().cpu().numpy()

        spikes_bin = (spikes > 0.5).astype(np.uint8)
        low = eng.v_rest - 12.0
        high = eng.v_thresh + 6.0
        norm_v = np.clip((voltages - low) / (high - low), 0.0, 1.0)
        region_activity = {
            name: round(float(spikes[idx].mean()) if len(idx) else 0.0, 4)
            for name, idx in zip(eng.region_names, eng._region_indices)
        }

        self._activity_seq += 1
        return {
            "seq": self._activity_seq,
            "visible_count": int(len(eng.visible_idx)),
            "spike_count": int(spikes_bin.sum()),
            "mean_v": round(float(norm_v.mean()), 4),
            "spikes_b64": self.encode_bytes(np.packbits(spikes_bin)),
            "v_b64": self.encode_bytes((norm_v * 255.0).astype(np.uint8)),
            "region_activity": region_activity,
            "total_spikes": eng.total_spikes_step,
        }

    def get_lif_trace(self) -> dict[str, Any]:
        eng = self._engine
        return {
            "labels": ["R1 (Retina)", "KC (Cuerpo del Hongo)", "DNp09 (Ataque)"],
            "samples": [
                [round(float(value), 2) for value in row] for row in eng.lif_trace
            ],
            "v_thresh": round(float(eng.v_thresh), 2),
            "v_rest": float(eng.v_rest),
        }

    def get_sampled_3d_activity(self, sample_size: int = 500) -> list[dict[str, Any]]:
        eng = self._engine
        dn_samples = min(20, max(0, sample_size // 5))
        uniform_n = max(0, sample_size - dn_samples)
        idx_uniform = (
            np.linspace(0, 19799, uniform_n, dtype=int)
            if uniform_n > 0
            else np.array([], dtype=int)
        )
        idx_dn = (
            np.linspace(19800, eng.N - 1, dn_samples, dtype=int)
            if dn_samples > 0
            else np.array([], dtype=int)
        )
        idx = np.concatenate([idx_uniform, idx_dn])
        v_sub = eng.v[idx].detach().cpu().numpy()
        s_sub = eng.spikes[idx].detach().cpu().numpy()
        c_sub = eng.coords_3d[idx]
        return [
            {
                "id": int(i),
                "x": round(float(c[0]), 3),
                "y": round(float(c[1]), 3),
                "z": round(float(c[2]), 3),
                "v": round(float(v), 2),
                "s": int(s),
            }
            for i, c, v, s in zip(idx, c_sub, v_sub, s_sub)
        ]
