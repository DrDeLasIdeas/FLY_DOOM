"""Thin FastAPI transport layer delegating orchestration to SimulationCoordinator."""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel

from .services.simulation_service import SimulationCoordinator

coordinator = SimulationCoordinator()
active_websocket: WebSocket | None = None


async def gemma_background_loop() -> None:
    while True:
        await asyncio.sleep(5.0)
        await coordinator.run_gemma_cycle()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(gemma_background_loop())
    try:
        yield
    finally:
        task.cancel()
        coordinator.persist_state(commit_partial=True)
        coordinator.env.close()


app = FastAPI(
    title="NeuroDoom OS — SOLID PPO & Drosophila Connectome Engine",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)


class ModulateRequest(BaseModel):
    v_thresh: float | None = None
    dopamine_lr: float | None = None
    sensory_gain: float | None = None
    noise_std: float | None = None


class DopaminePulseRequest(BaseModel):
    valence: float = 1.5


class TrainingRequest(BaseModel):
    enabled: bool | None = None
    greedy: bool | None = None
    reset: bool = False
    temperature: float | None = None
    reload: bool = False
    save: bool = True


class SystemControlRequest(BaseModel):
    running: bool | None = None
    save: bool = True


class ScenarioSwitchRequest(BaseModel):
    scenario_id: str
    skill: int | None = None


class SpeedControlRequest(BaseModel):
    target_fps: int | None = None
    tic_skip: int | None = None


@app.get("/api/health")
async def health_check():
    return coordinator.health_status()


@app.get("/api/system")
async def system_status():
    return {
        "status": "ok",
        "system_running": coordinator.system_running,
        "last_saved_at": coordinator.last_saved_at,
        "scenario_id": coordinator.env.scenario.id,
        "episodes": coordinator.agent.episode,
        "total_kills": getattr(coordinator.env, "total_kills", coordinator.agent.total_kills),
        "total_shots": getattr(coordinator.env, "total_shots", coordinator.agent.total_shots),
        "total_hits": getattr(coordinator.env, "total_hits", coordinator.agent.total_hits),
        "motor_gains": [
            round(float(g), 3)
            for g in coordinator.snn_engine.motor_plastic_gain.detach().cpu().numpy()
        ],
    }


@app.post("/api/system")
async def control_system(req: SystemControlRequest):
    async with coordinator.lock:
        if req.running is False:
            coordinator.system_running = False
            saved = coordinator.persist_state(commit_partial=True)
            coordinator.latest_gemma_state["neuro_hypothesis"] = (
                f"Sistema detenido. Aprendizaje guardado ({saved['total_kills']} bajas, "
                f"{saved['episodes']} episodios)."
            )
            return {"status": "stopped", **saved}
        if req.running is True:
            if not coordinator.agent.loaded:
                coordinator.agent.load()
                coordinator.snn_engine.load_plasticity_state(coordinator.agent.snn_state)
                coordinator._sync_env_totals_from_agent()
            coordinator.system_running = True
            saved = (
                coordinator.persist_state(commit_partial=False)
                if req.save
                else {
                    "system_running": True,
                    "last_saved_at": coordinator.last_saved_at,
                    "episodes": coordinator.agent.episode,
                    "total_kills": getattr(
                        coordinator.env, "total_kills", coordinator.agent.total_kills
                    ),
                    "total_shots": getattr(
                        coordinator.env, "total_shots", coordinator.agent.total_shots
                    ),
                    "total_hits": getattr(
                        coordinator.env, "total_hits", coordinator.agent.total_hits
                    ),
                }
            )
            coordinator.latest_gemma_state["neuro_hypothesis"] = (
                f"Sistema reanudado ({coordinator.env.scenario.name}, "
                f"{saved['total_kills']} bajas acumuladas)."
            )
            return {"status": "started", **saved}
        saved = coordinator.persist_state(commit_partial=True)
        return {"status": "saved", **saved}


@app.get("/api/scenarios")
async def list_scenarios():
    return coordinator.scenario_status()


@app.post("/api/scenario")
async def switch_scenario(req: ScenarioSwitchRequest):
    async with coordinator.lock:
        try:
            info = coordinator.switch_scenario(req.scenario_id, skill=req.skill)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"status": "switched", "scenario": info, "policy": coordinator.training_status()}


@app.post("/api/episode/reset")
async def reset_episode():
    async with coordinator.lock:
        return coordinator.reset_episode()


@app.post("/api/speed")
async def update_speed(req: SpeedControlRequest):
    async with coordinator.lock:
        return coordinator.set_speed(target_fps=req.target_fps, tic_skip=req.tic_skip)


@app.get("/api/training")
async def training_status():
    return coordinator.training_status()


@app.get("/api/gemma")
async def gemma_status():
    return coordinator.latest_gemma_state


@app.get("/api/connectome/topology")
async def connectome_topology():
    return coordinator.snn_engine.get_topology_asset()


@app.post("/api/training")
async def set_training(req: TrainingRequest):
    async with coordinator.lock:
        if req.reload:
            coordinator.agent.load()
            coordinator.snn_engine.load_plasticity_state(coordinator.agent.snn_state)
            coordinator.agent.buffer.clear()
            coordinator._sync_env_totals_from_agent()
        if req.reset:
            coordinator.snn_engine.reset_plasticity_state()
            coordinator.agent.reset()
            if hasattr(coordinator.env, "_reset_counters"):
                coordinator.env._reset_counters()
            for attr in ("total_kills", "total_shots", "total_hits"):
                if hasattr(coordinator.env, attr):
                    setattr(coordinator.env, attr, 0)
        if req.enabled is not None:
            coordinator.agent.training_enabled = req.enabled
        if req.greedy is not None:
            coordinator.agent.greedy = req.greedy
        if req.temperature is not None:
            coordinator.agent.temperature = float(np.clip(req.temperature, 0.2, 3.0))
        if req.save and not req.reset:
            coordinator.persist_state(commit_partial=False)
    return {"status": "updated", **coordinator.training_status()}


@app.post("/api/modulate")
async def manual_modulate(req: ModulateRequest):
    payload = {k: v for k, v in req.model_dump().items() if v is not None}
    coordinator.snn_engine.update_biophysical_params(payload)
    coordinator.latest_gemma_state.update(payload)
    coordinator.latest_gemma_state["neuro_hypothesis"] = (
        "Intervención manual aplicada desde la consola de conferencia."
    )
    coordinator.persist_state(commit_partial=False)
    return {"status": "updated", "params": payload}


@app.post("/api/dopamine-pulse")
async def trigger_dopamine_pulse(req: DopaminePulseRequest):
    coordinator.snn_engine.inject_dopamine_pulse(req.valence)
    return {
        "status": "injected",
        "dopamine_level": round(coordinator.snn_engine.dopamine_level, 3),
    }


@app.websocket("/ws/telemetry")
async def telemetry_websocket(websocket: WebSocket):
    global active_websocket
    await websocket.accept()
    previous = active_websocket
    active_websocket = websocket
    if previous is not None:
        try:
            await previous.close(code=4000, reason="replaced by newer telemetry session")
        except Exception:
            pass

    try:
        while True:
            t_start = time.perf_counter()
            if not coordinator.system_running:
                paused_packet = coordinator.build_paused_packet()
                if paused_packet is not None:
                    await websocket.send_json(paused_packet)
                    await asyncio.sleep(0.25)
                    continue

            async with coordinator.lock:
                packet = coordinator.step_simulation()

            await websocket.send_json(packet)
            frame_interval = 1.0 / float(max(5, coordinator.target_fps))
            elapsed = time.perf_counter() - t_start
            await asyncio.sleep(max(0.004, frame_interval - elapsed))
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        if active_websocket is websocket:
            active_websocket = None
