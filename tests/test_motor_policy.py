import numpy as np
import pytest
import torch

from backend.app import doom_bridge
from backend.app.doom_bridge import DoomFlyEnvironment
from backend.app.motor_policy import FEATURE_DIM, MotorPolicy


def test_build_features_shape_and_finiteness():
    policy = MotorPolicy(save_path="data/_test_policy_features.pt")
    retina = np.random.default_rng(0).integers(0, 255, (64, 64), dtype=np.uint8)
    dn = {"dn_left": 0.02, "dn_right": 0.05, "dn_move": 0.01, "dn_attack": 0.9}
    enemy = {"present": 1.0, "offset": -1.7, "size": 0.2, "centered": 0.0}
    feats = policy.build_features(retina, dn, enemy)

    assert feats.shape == (FEATURE_DIM,)
    assert feats.shape == (72,)
    assert np.isfinite(feats).all()
    assert feats[-4] == pytest.approx(1.0)
    assert feats[-3] == pytest.approx(-1.0)
    assert feats[-2] == pytest.approx(1.0)
    assert feats[-1] == pytest.approx(0.0)

    rgb = np.random.default_rng(1).integers(0, 255, (64, 64, 3), dtype=np.uint8)
    feats_rgb = policy.build_features(rgb, dn, {"present": 0.0})
    assert feats_rgb.shape == (FEATURE_DIM,)


def test_act_returns_valid_distribution():
    policy = MotorPolicy(save_path="data/_test_policy_act.pt")
    policy.training_enabled = False
    feats = np.zeros(FEATURE_DIM, dtype=np.float32)

    action, prob, probs = policy.act(feats)

    assert 0 <= action < 4
    assert len(probs) == 4
    assert sum(probs) == pytest.approx(1.0, abs=1e-4)
    assert probs[action] == pytest.approx(prob, abs=1e-4)

    greedy_action, _, greedy_probs = policy.act(feats, greedy=True)
    assert greedy_action == int(np.argmax(greedy_probs))


def test_supervised_learning_and_checkpoint_roundtrip(tmp_path):
    policy = MotorPolicy(save_path=str(tmp_path / "policy.pt"))
    rng = np.random.default_rng(3)
    features = rng.normal(size=(256, FEATURE_DIM)).astype(np.float32)
    actions = (features[:, 0] + features[:, 1] > 0).astype(np.int64)

    losses = policy.train_supervised(features, actions, epochs=30, batch_size=64, lr=1e-2)
    assert losses[-1] < losses[0]

    policy.episode = 4
    policy.total_kills = 7
    policy.save()

    restored = MotorPolicy(save_path=str(tmp_path / "policy.pt"))
    assert restored.load()
    assert restored.episode == 4
    assert restored.total_kills == 7
    for original, loaded in zip(policy.parameters(), restored.parameters()):
        assert torch.allclose(original, loaded)


def test_synthetic_env_tracks_shots_kills_and_reset(monkeypatch):
    monkeypatch.setattr(doom_bridge, "VIZDOOM_AVAILABLE", False)
    env = DoomFlyEnvironment()
    assert env.use_synthetic
    env.synthetic_episode_timeout = 1

    result = env.step(action_idx=2)
    assert result["ammo"] == pytest.approx(25.0)
    assert result["shots_fired"] == 1
    assert result["kills"] == 1
    assert result["enemy"]["present"] == 1.0
    assert result["enemy"]["centered"] == 1.0
    assert result["episode_finished"] is False
    assert result["shaped_reward"] > 1.0

    reset = env.step(action_idx=3)
    assert reset["episode_finished"] is True
    assert reset["action_name"] == "EPISODE_RESET"
    assert reset["last_episode"]["steps"] == 1
    assert reset["episode"] == 2
    assert reset["ammo"] == pytest.approx(env.ammo_max)


def test_value_head_checkpoint_is_backward_compatible(tmp_path):
    path = str(tmp_path / "old_policy.pt")
    policy = MotorPolicy(save_path=path)
    policy.episode = 3
    policy.total_kills = 5
    policy.save()

    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    ckpt["state_dict"] = {
        key: value
        for key, value in ckpt["state_dict"].items()
        if not key.startswith("value_head")
    }
    torch.save(ckpt, path)

    restored = MotorPolicy(save_path=path)
    assert restored.load()
    assert restored.episode == 3
    assert restored.total_kills == 5
    assert restored.status()["best_kills"] == 0


def test_fast_mode_disables_frame_encoding():
    env = DoomFlyEnvironment(force_synthetic=True, encode_frames=False, render_overlay=False)
    assert env.use_synthetic

    result = env.step(action_idx=3)
    assert result["frame_b64"] == ""
    assert result["retina_b64"] == ""
    assert result["retina_64"].shape == (64, 64)


def test_centered_attack_without_ammo_is_not_rewarded():
    env = DoomFlyEnvironment(force_synthetic=True)
    env.step(action_idx=3)
    env.last_ammo = 0.0

    result = env.step(action_idx=2)
    assert result["shots_fired"] == 0
    assert result["kills"] == 0
    assert result["enemy"]["centered"] == 1.0
    assert result["shaped_reward"] <= 0.0


def test_shots_never_below_kills_in_synthetic_episode():
    env = DoomFlyEnvironment(force_synthetic=True)
    env.synthetic_episode_timeout = 10_000
    for _ in range(60):
        env.step(action_idx=2)
        assert env.shots_fired >= env.kills
    summary = env._make_summary()
    assert summary["accuracy"] <= 1.0


def test_trainer_run_episode_smoke(tmp_path):
    from scripts.train_motor_policy import run_episode

    class DummySNN:
        def step_biophysics(self, retina, reward_signal, dt=1.0):
            return {
                "dn_left": 0.01,
                "dn_right": 0.01,
                "dn_move": 0.01,
                "dn_attack": 0.01,
            }

    policy = MotorPolicy(save_path=str(tmp_path / "trainer_policy.pt"))
    env = DoomFlyEnvironment(force_synthetic=True, encode_frames=False, render_overlay=False)
    env.synthetic_episode_timeout = 8

    summary, loss = run_episode(env, DummySNN(), policy, tic_skip=1, substeps=1, train=True)

    assert summary["steps"] == 8
    assert policy.episode == 1
    assert policy.total_shots >= policy.total_kills
    assert isinstance(loss, float)
    assert (tmp_path / "trainer_policy.pt").exists()
    env.close()


def test_snn_plasticity_and_kills_persist_across_stop_and_start(tmp_path):
    ckpt_path = str(tmp_path / "persisted_system.pt")
    policy = MotorPolicy(save_path=ckpt_path)
    policy.episode = 19
    policy.total_kills = 42
    policy.total_shots = 90
    policy.total_hits = 42
    policy.snn_state = {
        "motor_plastic_gain": [1.35, 0.85, 1.10, 1.75],
        "eligibility_trace": [0.1, -0.05, 0.02, 0.2],
        "v_thresh": -46.2,
        "dopamine_lr": 0.012,
        "sensory_gain": 22.0,
        "noise_std": 0.7,
        "dopamine_level": 0.4,
    }
    policy.save(extra_stats={"total_kills": 45, "best_kills": 45})

    restored = MotorPolicy(save_path=ckpt_path)
    assert restored.load()
    assert restored.episode == 19
    assert restored.total_kills == 45
    assert restored.best_kills == 45
    assert restored.snn_state["motor_plastic_gain"] == pytest.approx([1.35, 0.85, 1.10, 1.75])
    assert restored.snn_state["v_thresh"] == pytest.approx(-46.2)


