import json
import numpy as np
import pytest
import torch
from fastapi.testclient import TestClient

from backend.app.core.interfaces import EnvironmentAdapter, Neuromodulator, RLAgent
from backend.app.gemma_neuromodulator import GemmaNeuromodulatorAdapter
from backend.app.rl import PPOAgent, PPOConfig, RolloutBuffer
from backend.app.scenarios import ScenarioFactory, ScenarioRegistry
from backend.app.services.simulation_service import SimulationCoordinator
from backend.app.vision import VisualBufferConfig, VisualBufferProcessor


def test_visual_buffer_processor_pipeline_and_mosaic():
    proc = VisualBufferProcessor(VisualBufferConfig(width=84, height=84, stack_size=4))
    assert proc.output_shape == (4, 84, 84)

    frame_a = np.zeros((240, 320, 3), dtype=np.uint8)
    frame_a[:, :, 0] = 200
    stack_1 = proc.process(frame_a)
    assert stack_1.shape == (4, 84, 84)
    assert stack_1.dtype == np.float32
    assert 0.0 <= stack_1.min() <= stack_1.max() <= 1.0
    assert np.allclose(stack_1[0], stack_1[3])

    frame_b = np.full((240, 320, 3), 240, dtype=np.uint8)
    stack_2 = proc.process(frame_b)
    assert stack_2[3].mean() > stack_2[0].mean()

    retina = proc.compute_retina_64(frame_a)
    assert retina.shape == (64, 64)
    assert retina.dtype == np.uint8

    mosaic_b64 = proc.encode_stack_mosaic_b64()
    assert len(mosaic_b64) > 100

    proc.reset()
    assert np.allclose(proc.latest_frame(), 0.0)


def test_scenario_registry_all_five_and_custom_dropin(tmp_path):
    registry = ScenarioRegistry()
    ids = set(registry.list_ids())
    assert {
        "defend_the_center",
        "basic",
        "defend_the_line",
        "deadly_corridor",
        "health_gathering",
    }.issubset(ids)

    for sid in ids:
        cfg = registry.get(sid)
        assert len(cfg.actions) >= 3
        for act in cfg.actions:
            assert len(act.buttons) == len(cfg.buttons)

    # OCP: drop-in custom scenario JSON without editing core source code
    custom_json = tmp_path / "custom_arena.json"
    custom_json.write_text(
        json.dumps(
            {
                "id": "custom_arena",
                "name": "Custom Arena",
                "description": "Custom WAD test",
                "cfg_file": "basic.cfg",
                "buttons": ["MOVE_LEFT", "MOVE_RIGHT", "ATTACK"],
                "actions": [
                    {"name": "MOVE_LEFT", "label": "Left", "buttons": [1, 0, 0]},
                    {"name": "MOVE_RIGHT", "label": "Right", "buttons": [0, 1, 0]},
                    {"name": "ATTACK", "label": "Attack", "buttons": [0, 0, 1]},
                ],
                "reward_shaper": "basic",
                "is_combat": True,
            }
        ),
        encoding="utf-8",
    )
    loaded = registry.register_json(custom_json)
    assert loaded.id == "custom_arena"
    assert registry.get("custom_arena").name == "Custom Arena"


def test_scenario_factory_creates_lsp_adapters():
    factory = ScenarioFactory()
    for sid in ("defend_the_center", "basic", "deadly_corridor", "health_gathering"):
        adapter = factory.create(sid, force_synthetic=True, tic_skip=2)
        assert isinstance(adapter, EnvironmentAdapter)
        obs0 = adapter.reset()
        assert obs0.raw_frame.shape == (240, 320, 3)
        obs1 = adapter.step(0)
        assert obs1.scenario_id == sid
        assert np.isfinite(obs1.shaped_reward)
        adapter.close()


def test_rollout_buffer_gae_and_ppo_update_and_hot_swap(tmp_path):
    cfg = PPOConfig(
        rollout_steps=16,
        minibatch_size=8,
        update_epochs=2,
        checkpoint_dir=str(tmp_path),
    )
    agent = PPOAgent(
        scenario_id="defend_the_center",
        action_labels=["TURN_LEFT", "TURN_RIGHT", "ATTACK", "IDLE"],
        config=cfg,
    )
    assert isinstance(agent, RLAgent)

    rng = np.random.default_rng(11)
    obs = rng.uniform(0.0, 1.0, size=(4, 84, 84)).astype(np.float32)
    loss_returned = None
    for step in range(16):
        decision = agent.select_action(obs)
        assert 0 <= decision.action_idx < 4
        assert sum(decision.action_probs) == pytest.approx(1.0, abs=1e-4)
        next_obs = rng.uniform(0.0, 1.0, size=(4, 84, 84)).astype(np.float32)
        res = agent.observe_transition(
            obs, decision, reward=0.5 if step % 3 == 0 else -0.05, done=(step == 15), next_obs=next_obs
        )
        if res is not None:
            loss_returned = res
        obs = next_obs

    assert loss_returned is not None
    assert np.isfinite(loss_returned)
    assert agent.updates == 1
    assert 0.0 <= agent.exploration_rate <= 1.0

    agent.on_episode_end({"episode": 1, "reward": 3.2, "kills": 2, "shots": 4, "hits": 2, "accuracy": 0.5, "steps": 16})
    assert agent.episode == 1

    # Save & restore roundtrip
    restored = PPOAgent(
        scenario_id="defend_the_center",
        action_labels=["TURN_LEFT", "TURN_RIGHT", "ATTACK", "IDLE"],
        config=cfg,
    )
    assert restored.load()
    assert restored.episode == 1
    for p1, p2 in zip(agent.network.parameters(), restored.network.parameters()):
        assert torch.allclose(p1, p2)

    # Hot-swap to a 7-action scenario (deadly_corridor)
    agent.switch_scenario(
        "deadly_corridor",
        ["TURN_LEFT", "TURN_RIGHT", "MOVE_FORWARD", "MOVE_LEFT", "MOVE_RIGHT", "ATTACK", "FORWARD_ATTACK"],
    )
    assert agent.n_actions == 7
    dec7 = agent.select_action(obs)
    assert len(dec7.action_probs) == 7


def test_simulation_coordinator_and_api_controls(tmp_path, monkeypatch):
    from backend.app import main as main_mod
    from backend.app.env import vizdoom_adapter

    monkeypatch.setattr(vizdoom_adapter, "VIZDOOM_AVAILABLE", False)

    coord = SimulationCoordinator(initial_scenario="defend_the_center")
    coord.agent.config.checkpoint_dir = str(tmp_path)
    coord.agent.save_path = str(tmp_path / "ppo_defend_the_center.pt")
    monkeypatch.setattr(main_mod, "coordinator", coord)

    packet = coord.step_simulation()
    assert packet["visual_buffer_shape"] == [4, 84, 84]
    assert len(packet["visual_buffer_b64"]) > 100
    assert packet["policy"]["algorithm"] == "PPO-CNN"
    assert packet["scenario"]["id"] == "defend_the_center"

    client = TestClient(main_mod.app)
    r_health = client.get("/api/health")
    assert r_health.status_code == 200
    assert r_health.json()["algorithm"] == "PPO-CNN"

    r_switch = client.post("/api/scenario", json={"scenario_id": "health_gathering"})
    assert r_switch.status_code == 200
    assert r_switch.json()["scenario"]["id"] == "health_gathering"
    assert len(r_switch.json()["scenario"]["actions"]) == 5

    r_speed = client.post("/api/speed", json={"target_fps": 45, "tic_skip": 4})
    assert r_speed.status_code == 200
    assert r_speed.json()["target_fps"] == 45
    assert r_speed.json()["tic_skip"] == 4

    r_reset = client.post("/api/episode/reset")
    assert r_reset.status_code == 200
    assert r_reset.json()["status"] == "episode_reset"
    coord.env.close()


def test_immediate_terminal_step_preserves_reward_and_summary():
    factory = ScenarioFactory()
    adapter = factory.create("defend_the_center", force_synthetic=True, tic_skip=2)
    adapter.set_episode_timeout(3)
    adapter.reset()

    obs1 = adapter.step(2)
    assert obs1.episode_finished is False
    obs2 = adapter.step(2)
    assert obs2.episode_finished is False
    obs3 = adapter.step(2)
    assert obs3.episode_finished is True
    assert obs3.last_episode["steps"] == 3
    assert obs3.action_name == "ATTACK"
    assert obs3.shaped_reward != 0.0
    adapter.close()


def test_same_action_count_scenario_switch_rebuilds_weights_and_greedy_skips_rollout(tmp_path):
    cfg = PPOConfig(rollout_steps=8, minibatch_size=4, checkpoint_dir=str(tmp_path))
    agent = PPOAgent(
        scenario_id="defend_the_center",
        action_labels=["TURN_LEFT", "TURN_RIGHT", "ATTACK", "IDLE"],
        config=cfg,
    )
    with torch.no_grad():
        for p in agent.network.actor_head.parameters():
            p.fill_(3.14)

    # Switch to another 4-action scenario with no saved checkpoint -> must NOT keep 3.14 weights
    agent.switch_scenario(
        "basic",
        ["MOVE_LEFT", "MOVE_RIGHT", "ATTACK", "IDLE"],
        load_if_exists=True,
    )
    actor_max = max(float(p.abs().max().item()) for p in agent.network.actor_head.parameters())
    assert actor_max < 1.0

    # Greedy mode must never pollute on-policy RolloutBuffer
    agent.greedy = True
    obs = np.zeros((4, 84, 84), dtype=np.float32)
    dec = agent.select_action(obs)
    assert agent.status()["exploration_rate"] == 0.0
    agent.observe_transition(obs, dec, reward=1.0, done=False, next_obs=obs)
    assert len(agent.buffer) == 0


def test_async_shadow_ppo_update_and_gemma_neuromodulator_protocol(tmp_path):
    import asyncio

    adapter = GemmaNeuromodulatorAdapter(ollama_host="http://127.0.0.1:9", timeout_sec=0.2)
    assert isinstance(adapter, Neuromodulator)
    res = asyncio.run(
        adapter.modulate(
            {"mushroom_body_kc": 0.004},
            {"v_thresh": -45.0, "dopamine_lr": 0.008, "sensory_gain": 18.0, "noise_std": 0.8},
        )
    )
    assert res["status"] == "HOMEOSTATIC_FALLBACK"

    cfg = PPOConfig(rollout_steps=8, minibatch_size=4, update_epochs=2, checkpoint_dir=str(tmp_path))
    agent = PPOAgent(scenario_id="basic", config=cfg)
    rng = np.random.default_rng(5)
    obs = rng.uniform(0.0, 1.0, size=(4, 84, 84)).astype(np.float32)
    for _ in range(8):
        dec = agent.select_action(obs)
        agent.record_step(obs, dec, reward=0.25, done=False)

    job = agent.prepare_async_update(obs, False)
    assert job is not None
    assert len(agent.buffer) == 0
    shadow_out = agent.run_shadow_update(job)
    loss = agent.commit_shadow_update(shadow_out)
    assert np.isfinite(loss)
    assert agent.updates == 1

