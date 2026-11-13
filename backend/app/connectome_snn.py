"""Pure Biophysical Spiking Neural Network Engine (LIF + Dopamine-Modulated R-STDP).

Uses sparse COO matrix multiplication (`torch.sparse.mm`) exclusively without
densifying the 20k×20k connectome. Telemetry serialization is delegated to
`ConnectomeTelemetrySerializer` (SRP).
"""

from __future__ import annotations

import os
import time
import numpy as np
import torch

from .config import settings
from .connectome_serializer import ConnectomeTelemetrySerializer


class DrosophilaConnectomeEngine:
    @staticmethod
    def _select_device() -> torch.device:
        """Selects best accelerator supporting sparse COO matmul (CPU NEON fallback on MPS)."""
        if torch.cuda.is_available():
            return torch.device("cuda")

        if torch.backends.mps.is_available():
            try:
                probe = torch.sparse_coo_tensor(
                    torch.tensor([[0], [0]]),
                    torch.tensor([1.0]),
                    (2, 2),
                    device="mps",
                ).coalesce()
                torch.sparse.mm(probe, torch.ones((2, 1), device="mps"))
                return torch.device("mps")
            except (NotImplementedError, RuntimeError):
                pass

        torch.set_num_threads(max(4, os.cpu_count() or 4))
        return torch.device("cpu")

    def __init__(self, connectome_path: str | None = None):
        path = connectome_path or settings.connectome_path
        if not os.path.exists(path):
            from scripts.generate_connectome_graph import build_connectome_artifact

            build_connectome_artifact(path)

        self.device = self._select_device()

        data = np.load(path)
        self.N = int(data["num_neurons"])
        pre_idx = torch.tensor(data["pre_idx"], dtype=torch.long, device=self.device)
        post_idx = torch.tensor(data["post_idx"], dtype=torch.long, device=self.device)
        weights = torch.tensor(data["weights"], dtype=torch.float32, device=self.device)
        self.coords_3d = data["coords_3d"]
        self.num_synapses = int(len(weights))
        weight_values = np.asarray(data["weights"], dtype=np.float32)
        self.synapse_stats = {
            "num_synapses": int(weight_values.size),
            "excitatory": int((weight_values > 0).sum()),
            "inhibitory": int((weight_values < 0).sum()),
            "density": round(float(weight_values.size / (self.N * self.N)), 6),
        }

        indices = torch.stack([post_idx, pre_idx], dim=0)
        self.W = torch.sparse_coo_tensor(
            indices, weights, (self.N, self.N), device=self.device
        ).coalesce()

        self._load_visual_metadata(data)

        self.v_rest = settings.v_rest
        self.v_thresh = settings.v_thresh
        self.v_reset = settings.v_reset
        self.tau_m = settings.tau_m
        self.tau_syn = settings.tau_syn
        self.dopamine_lr = settings.dopamine_lr
        self.sensory_gain = settings.sensory_gain
        self.noise_std = settings.noise_std

        self.v = torch.full((self.N,), self.v_rest, dtype=torch.float32, device=self.device)
        self.trace_neurons = np.array([0, 8192, 19975], dtype=np.int64)
        self._trace_idx_t = torch.as_tensor(
            self.trace_neurons, dtype=torch.long, device=self.device
        )
        self.lif_trace = np.full((len(self.trace_neurons), 64), self.v_rest, dtype=np.float32)
        self.i_syn = torch.zeros((self.N,), dtype=torch.float32, device=self.device)
        self._i_ext = torch.zeros((self.N,), dtype=torch.float32, device=self.device)
        self._noise_buf = torch.zeros((self.N,), dtype=torch.float32, device=self.device)
        self.spikes = torch.zeros((self.N,), dtype=torch.float32, device=self.device)
        self.spike_trace = torch.zeros((self.N,), dtype=torch.float32, device=self.device)
        self.eligibility_trace = torch.zeros((4,), dtype=torch.float32, device=self.device)

        self.mbon_slice = slice(19000, 19500)
        self.dn_left_slice = slice(19800, 19850)
        self.dn_right_slice = slice(19850, 19900)
        self.dn_move_slice = slice(19900, 19950)
        self.dn_attack_slice = slice(19950, 20000)

        self.motor_plastic_gain = torch.ones((4,), dtype=torch.float32, device=self.device)
        self.dopamine_level = 0.0
        self.total_spikes_step = 0
        self.last_latency_ms = 0.0
        self._serializer = ConnectomeTelemetrySerializer(self)

    def _load_visual_metadata(self, data) -> None:
        if "visible_idx" in data:
            self.visible_idx = np.asarray(data["visible_idx"], dtype=np.int64)
            self.regions = np.asarray(data["regions"], dtype=np.uint8)
            self.region_names = [str(name) for name in data["region_names"]]
            raw_edges = np.asarray(data["display_edges"], dtype=np.int64).reshape(-1, 2)
            raw_sign = np.asarray(data["edge_sign"], dtype=np.int8)
            raw_weight = np.asarray(data["edge_weight"], dtype=np.float32)
        else:
            self.visible_idx = np.linspace(0, self.N - 1, 4096, dtype=np.int64)
            self.regions = np.zeros(self.N, dtype=np.uint8)
            self.region_names = ["Conectoma"]
            raw_edges = np.zeros((0, 2), dtype=np.int64)
            raw_sign = np.zeros((0,), dtype=np.int8)
            raw_weight = np.zeros((0,), dtype=np.float32)

        self.visible_positions = self.coords_3d[self.visible_idx].astype(np.float32)
        self.visible_regions = self.regions[self.visible_idx]
        self._visible_idx_t = torch.as_tensor(
            self.visible_idx, dtype=torch.long, device=self.device
        )

        self.pos_in_visible = np.full(self.N, -1, dtype=np.int64)
        self.pos_in_visible[self.visible_idx] = np.arange(
            len(self.visible_idx), dtype=np.int64
        )

        self.ghost_idx = np.setdiff1d(
            np.arange(self.N, dtype=np.int64), self.visible_idx
        ).astype(np.int32)
        self.ghost_positions = self.coords_3d[self.ghost_idx].astype(np.float32)
        self.ghost_regions = self.regions[self.ghost_idx]

        if len(raw_edges):
            local_edges = self.pos_in_visible[raw_edges]
            valid = (local_edges >= 0).all(axis=1)
            self.display_edges_local = local_edges[valid].astype(np.int32)
            self.edge_sign = raw_sign[valid]
            self.edge_weight = raw_weight[valid]
        else:
            self.display_edges_local = np.zeros((0, 2), dtype=np.int32)
            self.edge_sign = np.zeros((0,), dtype=np.int8)
            self.edge_weight = np.zeros((0,), dtype=np.float32)

        self.region_counts = (
            np.bincount(self.visible_regions, minlength=len(self.region_names))
            .astype(int)
            .tolist()
        )
        self._region_indices = [
            np.flatnonzero(self.visible_regions == group)
            for group in range(len(self.region_names))
        ]

    # Delegated serialization helpers (preserving existing API surface)
    def get_topology_asset(self) -> dict:
        return self._serializer.get_topology_asset()

    def get_dynamic_activity(self) -> dict:
        return self._serializer.get_dynamic_activity()

    def get_lif_trace(self) -> dict:
        return self._serializer.get_lif_trace()

    def get_sampled_3d_activity(self, sample_size: int = 500) -> list[dict]:
        return self._serializer.get_sampled_3d_activity(sample_size)

    def inject_dopamine_pulse(self, valence: float) -> None:
        self.dopamine_level = float(np.clip(self.dopamine_level + valence, -5.0, 5.0))

    def update_biophysical_params(self, params: dict) -> None:
        if "v_thresh" in params:
            self.v_thresh = float(np.clip(params["v_thresh"], -49.0, -41.0))
        if "dopamine_lr" in params:
            self.dopamine_lr = float(np.clip(params["dopamine_lr"], 0.001, 0.05))
        if "sensory_gain" in params:
            self.sensory_gain = float(np.clip(params["sensory_gain"], 8.0, 30.0))
        if "noise_std" in params:
            self.noise_std = float(np.clip(params["noise_std"], 0.2, 2.5))

    def get_plasticity_state(self) -> dict:
        return {
            "motor_plastic_gain": [
                float(g) for g in self.motor_plastic_gain.detach().cpu().numpy().tolist()
            ],
            "eligibility_trace": [
                float(e) for e in self.eligibility_trace.detach().cpu().numpy().tolist()
            ],
            "v_thresh": float(self.v_thresh),
            "dopamine_lr": float(self.dopamine_lr),
            "sensory_gain": float(self.sensory_gain),
            "noise_std": float(self.noise_std),
            "dopamine_level": float(self.dopamine_level),
        }

    def load_plasticity_state(self, state: dict | None) -> None:
        if not state or not isinstance(state, dict):
            return
        gains = state.get("motor_plastic_gain")
        if isinstance(gains, (list, tuple)) and len(gains) == 4:
            self.motor_plastic_gain = torch.clamp(
                torch.tensor(gains, dtype=torch.float32, device=self.device), 0.4, 2.5
            )
        elig = state.get("eligibility_trace")
        if isinstance(elig, (list, tuple)) and len(elig) == 4:
            self.eligibility_trace = torch.tensor(
                elig, dtype=torch.float32, device=self.device
            )
        self.update_biophysical_params(state)
        if "dopamine_level" in state:
            self.dopamine_level = float(np.clip(state["dopamine_level"], -5.0, 5.0))

    def reset_plasticity_state(self) -> None:
        self.motor_plastic_gain = torch.ones((4,), dtype=torch.float32, device=self.device)
        self.eligibility_trace = torch.zeros((4,), dtype=torch.float32, device=self.device)
        self.dopamine_level = 0.0
        self.v_thresh = settings.v_thresh
        self.dopamine_lr = settings.dopamine_lr
        self.sensory_gain = settings.sensory_gain
        self.noise_std = settings.noise_std

    def _integrate_substep(self, sensory_current: torch.Tensor, reward_signal: float, dt: float) -> None:
        """Executes a single allocation-free LIF + R-STDP integration substep."""
        self._i_ext.zero_()
        self._i_ext[0:4096] = sensory_current

        self.dopamine_level = 0.88 * self.dopamine_level + 0.12 * float(reward_signal)
        if self.dopamine_level > 0.01:
            self._i_ext[19500:19650] = 14.0 * self.dopamine_level
        elif self.dopamine_level < -0.01:
            self._i_ext[19650:19800] = 14.0 * abs(self.dopamine_level)

        syn_input = torch.sparse.mm(self.W, self.spikes.unsqueeze(1)).squeeze(1)
        self.i_syn.add_(syn_input - self.i_syn, alpha=dt / self.tau_syn)

        self._noise_buf.normal_(0.0, self.noise_std)
        dv = ((self.v_rest - self.v) + self.i_syn + self._i_ext + self._noise_buf) * (
            dt / self.tau_m
        )
        self.v.add_(dv)

        fired = self.v >= self.v_thresh
        self.spikes = fired.float()
        self.v.masked_fill_(fired, self.v_reset)
        self.spike_trace.mul_(0.90).add_(self.spikes, alpha=0.10)

        dn_means = torch.stack(
            [
                self.spike_trace[self.dn_left_slice].mean(),
                self.spike_trace[self.dn_right_slice].mean(),
                self.spike_trace[self.dn_move_slice].mean(),
                self.spike_trace[self.dn_attack_slice].mean(),
            ]
        )
        active_drive = dn_means * self.motor_plastic_gain
        self.eligibility_trace.mul_(0.92).add_(active_drive - active_drive.mean())

        if abs(self.dopamine_level) > 0.005:
            delta_g = self.dopamine_lr * self.dopamine_level * self.eligibility_trace
            self.motor_plastic_gain.add_(delta_g).clamp_(0.4, 2.5)

    def _readout_rates(self) -> dict[str, float]:
        dn_means = torch.stack(
            [
                self.spike_trace[self.dn_left_slice].mean(),
                self.spike_trace[self.dn_right_slice].mean(),
                self.spike_trace[self.dn_move_slice].mean(),
                self.spike_trace[self.dn_attack_slice].mean(),
            ]
        ) * self.motor_plastic_gain
        dn_vals = dn_means.detach().cpu().tolist()
        return {
            "retina_r1_r8": round(float(self.spikes[0:4096].mean().item()), 4),
            "optic_lobe_t4_t5": round(float(self.spikes[4096:8192].mean().item()), 4),
            "mushroom_body_kc": round(float(self.spikes[8192:16384].mean().item()), 4),
            "central_complex": round(float(self.spikes[16384:19000].mean().item()), 4),
            "mbon_valence": round(float(self.spikes[self.mbon_slice].mean().item()), 4),
            "dan_dopamine": round(float(self.spikes[19500:19800].mean().item()), 4),
            "dn_left": round(float(dn_vals[0]), 4),
            "dn_right": round(float(dn_vals[1]), 4),
            "dn_move": round(float(dn_vals[2]), 4),
            "dn_attack": round(float(dn_vals[3]), 4),
        }

    @torch.no_grad()
    def step_frame(
        self,
        visual_frame_64x64: np.ndarray,
        reward_signal: float = 0.0,
        *,
        substeps: int = 4,
        dt: float = 1.0,
    ) -> dict[str, float]:
        """Optimized multi-substep frame integration (converts retina once per visual frame)."""
        t0 = time.perf_counter()
        sensory_current = (
            torch.as_tensor(
                np.ascontiguousarray(visual_frame_64x64).reshape(-1),
                dtype=torch.float32,
                device=self.device,
            )
            * (self.sensory_gain / 255.0)
        )
        k = max(1, int(substeps))
        trace_samples = np.empty((len(self.trace_neurons), k), dtype=np.float32)

        for i in range(k):
            self._integrate_substep(
                sensory_current, reward_signal if i == 0 else 0.0, dt=dt
            )
            trace_samples[:, i] = self.v[self._trace_idx_t].detach().cpu().numpy()

        self.lif_trace = np.roll(self.lif_trace, -k, axis=1)
        self.lif_trace[:, -k:] = trace_samples
        self.total_spikes_step = int(self.spikes.sum().item())
        rates = self._readout_rates()
        self.last_latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return rates

    @torch.no_grad()
    def step_biophysics(
        self, visual_frame_64x64: np.ndarray, reward_signal: float = 0.0, dt: float = 1.0
    ) -> dict[str, float]:
        return self.step_frame(visual_frame_64x64, reward_signal, substeps=1, dt=dt)
