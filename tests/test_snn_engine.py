import os
import base64
import asyncio
import numpy as np
from scripts.generate_connectome_graph import build_connectome_artifact
from backend.app.connectome_snn import DrosophilaConnectomeEngine
from backend.app.doom_bridge import DoomFlyEnvironment
from backend.app.gemma_neuromodulator import query_local_gemma_neuromodulator


def test_connectome_artifact_generation(tmp_path):
    out_file = str(tmp_path / "test_connectome.npz")
    build_connectome_artifact(output_path=out_file, num_neurons=20000)
    assert os.path.exists(out_file)
    data = np.load(out_file)
    assert int(data["num_neurons"]) == 20000
    assert data["coords_3d"].shape == (20000, 3)


def test_lif_biophysics_and_rstdp_plasticity(tmp_path):
    out_file = str(tmp_path / "test_connectome.npz")
    build_connectome_artifact(output_path=out_file, num_neurons=20000)
    engine = DrosophilaConnectomeEngine(connectome_path=out_file)

    dummy_retina = np.full((64, 64), 200, dtype=np.uint8)
    rates = engine.step_biophysics(dummy_retina, reward_signal=1.5, dt=1.0)

    assert "retina_r1_r8" in rates
    assert "mushroom_body_kc" in rates
    assert "dn_attack" in rates
    assert engine.W.is_sparse
    assert engine.last_latency_ms < 250.0

    sampled_3d = engine.get_sampled_3d_activity(100)
    assert len(sampled_3d) == 100
    assert {"id", "x", "y", "z", "v", "s"}.issubset(sampled_3d[0].keys())


def test_connectome_topology_asset(tmp_path):
    out_file = str(tmp_path / "test_connectome.npz")
    build_connectome_artifact(output_path=out_file, num_neurons=20000)
    engine = DrosophilaConnectomeEngine(connectome_path=out_file)

    asset = engine.get_topology_asset()
    assert asset["num_visible"] == 4096
    assert len(asset["region_names"]) == 12

    positions = np.frombuffer(
        base64.b64decode(asset["positions_b64"]), dtype=np.float32
    ).reshape(-1, 3)
    regions = np.frombuffer(base64.b64decode(asset["regions_b64"]), dtype=np.uint8)
    edges = np.frombuffer(
        base64.b64decode(asset["edges_b64"]), dtype=np.int32
    ).reshape(-1, 2)

    assert positions.shape == (4096, 3)
    assert regions.shape == (4096,)
    assert len(edges) > 0
    assert edges.min() >= 0
    assert edges.max() < 4096
    assert len(asset["region_counts"]) == 12

    assert asset["num_ghost"] == 20000 - 4096
    ghost_positions = np.frombuffer(
        base64.b64decode(asset["ghost_positions_b64"]), dtype=np.float32
    ).reshape(-1, 3)
    ghost_regions = np.frombuffer(
        base64.b64decode(asset["ghost_regions_b64"]), dtype=np.uint8
    )
    visible_idx = np.frombuffer(
        base64.b64decode(asset["visible_idx_b64"]), dtype=np.int32
    )
    assert ghost_positions.shape == (20000 - 4096, 3)
    assert ghost_regions.shape == (20000 - 4096,)
    assert visible_idx.shape == (4096,)
    assert visible_idx.max() < 20000
    assert asset["synapse_stats"]["num_synapses"] == engine.num_synapses
    assert 0.0 < asset["synapse_stats"]["density"] < 1.0

    assert len(asset["meshes"]) == 12
    for mesh in asset["meshes"]:
        vertices = np.frombuffer(
            base64.b64decode(mesh["vertices_b64"]), dtype=np.float32
        ).reshape(-1, 3)
        faces = np.frombuffer(base64.b64decode(mesh["faces_b64"]), dtype=np.uint32)
        assert len(vertices) >= 4
        assert len(faces) >= 3
        assert faces.max() < len(vertices)


def test_dynamic_activity_bitfields(tmp_path):
    out_file = str(tmp_path / "test_connectome.npz")
    build_connectome_artifact(output_path=out_file, num_neurons=20000)
    engine = DrosophilaConnectomeEngine(connectome_path=out_file)
    engine.step_biophysics(np.full((64, 64), 180, dtype=np.uint8), reward_signal=1.0)

    activity = engine.get_dynamic_activity()
    assert activity["visible_count"] == 4096

    spikes = np.unpackbits(
        np.frombuffer(base64.b64decode(activity["spikes_b64"]), dtype=np.uint8)
    )
    voltages = np.frombuffer(
        base64.b64decode(activity["v_b64"]), dtype=np.uint8
    )

    assert spikes.shape == (4096,)
    assert voltages.shape == (4096,)
    assert set(activity["region_activity"]) == set(engine.region_names)
    assert activity["spike_count"] == int(spikes.sum())
    assert 0.0 <= activity["mean_v"] <= 1.0

    trace = engine.get_lif_trace()
    assert len(trace["samples"]) == 3
    assert len(trace["samples"][0]) == 64
    assert trace["v_rest"] == engine.v_rest


def test_doom_bridge_step_and_retina_encoding():
    env = DoomFlyEnvironment()
    rates = {"dn_left": 0.01, "dn_right": 0.05, "dn_move": 0.02, "dn_attack": 0.12}
    result = env.step(rates)
    assert result["retina_64"].shape == (64, 64)
    assert len(result["frame_b64"]) > 100
    assert result["action_name"] == "ATTACK (DNp09)"


def test_gemma_neuromodulator_fallback():
    telemetry = {"mushroom_body_kc": 0.005}
    params = {"v_thresh": -45.0, "dopamine_lr": 0.008, "sensory_gain": 18.0, "noise_std": 0.8}
    res = asyncio.run(query_local_gemma_neuromodulator(telemetry, params))
    assert -49.0 <= res["v_thresh"] <= -41.0
    assert "neuro_hypothesis" in res
