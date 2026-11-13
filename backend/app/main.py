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

coordinator: SimulationCoordinator | None = None
active_websocket: WebSocket | None = None


def get_coordinator() -> SimulationCoordinator:
    """Lazy singleton accessor — avoids opening ViZDoom at module import time."""
    global coordinator
    if coordinator is None:
        coordinator = SimulationCoordinator()
    return coordinator


async def gemma_background_loop() -> None:
    while True:
        await asyncio.sleep(5.0)
        await get_coordinator().run_gemma_cycle()


@asynccontextmanager
async def lifespan(app: FastAPI):
    coord = get_coordinator()
    task = asyncio.create_task(gemma_background_loop())
    try:
        yield
    finally:
        task.cancel()
        await coord.shutdown()


app = FastAPI(
    title="NeuroDoom OS — SOLID PPO & Drosophila Connectome Engine",
    version="3.1.0",
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
    return get_coordinator().health_status()


@app.get("/api/system")
async def system_status():
    coord = get_coordinator()
    return {
        "status": "ok",
        "system_running": coord.system_running,
        "last_saved_at": coord.last_saved_at,
        "scenario_id": coord.env.scenario.id,
        "episodes": coord.agent.episode,
        "total_kills": getattr(coord.env, "total_kills", coord.agent.total_kills),
        "total_shots": getattr(coord.env, "total_shots", coord.agent.total_shots),
        "total_hits": getattr(coord.env, "total_hits", coord.agent.total_hits),
        "motor_gains": [
            round(float(g), 3)
            for g in coord.snn_engine.motor_plastic_gain.detach().cpu().numpy()
        ],
    }


@app.post("/api/system")
async def control_system(req: SystemControlRequest):
    coord = get_coordinator()
    async with coord.lock:
        if req.running is False:
            coord.system_running = False
            saved = coord.persist_state(commit_partial=True)
            coord.latest_gemma_state["neuro_hypothesis"] = (
                f"Sistema detenido. Aprendizaje guardado ({saved['total_kills']} bajas, "
                f"{saved['episodes']} episodios)."
            )
            return {"status": "stopped", **saved}
        if req.running is True:
            if not coord.agent.loaded:
                coord.agent.load()
                coord.snn_engine.load_plasticity_state(coord.agent.snn_state)
                coord._sync_env_totals_from_agent()
            coord.system_running = True
            saved = (
                coord.persist_state(commit_partial=False)
                if req.save
                else {
                    "system_running": True,
                    "last_saved_at": coord.last_saved_at,
                    "episodes": coord.agent.episode,
                    "total_kills": getattr(
                        coord.env, "total_kills", coord.agent.total_kills
                    ),
                    "total_shots": getattr(
                        coord.env, "total_shots", coord.agent.total_shots
                    ),
                    "total_hits": getattr(
                        coord.env, "total_hits", coord.agent.total_hits
                    ),
                }
            )
            coord.latest_gemma_state["neuro_hypothesis"] = (
                f"Sistema reanudado ({coord.env.scenario.name}, "
                f"{saved['total_kills']} bajas acumuladas)."
            )
            return {"status": "started", **saved}
        saved = coord.persist_state(commit_partial=True)
        return {"status": "saved", **saved}


@app.get("/api/scenarios")
async def list_scenarios():
    return get_coordinator().scenario_status()


@app.post("/api/scenario")
async def switch_scenario(req: ScenarioSwitchRequest):
    coord = get_coordinator()
    async with coord.lock:
        try:
            info = coord.switch_scenario(req.scenario_id, skill=req.skill)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"status": "switched", "scenario": info, "policy": coord.training_status()}


@app.post("/api/episode/reset")
async def reset_episode():
    coord = get_coordinator()
    async with coord.lock:
        return coord.reset_episode()


@app.post("/api/speed")
async def update_speed(req: SpeedControlRequest):
    coord = get_coordinator()
    async with coord.lock:
        return coord.set_speed(target_fps=req.target_fps, tic_skip=req.tic_skip)


@app.get("/api/training")
async def training_status():
    return get_coordinator().training_status()


@app.get("/api/gemma")
async def gemma_status():
    return get_coordinator().latest_gemma_state


@app.get("/api/connectome/topology")
async def connectome_topology():
    return get_coordinator().snn_engine.get_topology_asset()


@app.post("/api/training")
async def set_training(req: TrainingRequest):
    coord = get_coordinator()
    async with coord.lock:
        if req.reload:
            coord.agent.load()
            coord.snn_engine.load_plasticity_state(coord.agent.snn_state)
            coord.agent.buffer.clear()
            coord._sync_env_totals_from_agent()
        if req.reset:
            coord.snn_engine.reset_plasticity_state()
            coord.agent.reset()
            if hasattr(coord.env, "_reset_counters"):
                coord.env._reset_counters()
            for attr in ("total_kills", "total_shots", "total_hits"):
                if hasattr(coord.env, attr):
                    setattr(coord.env, attr, 0)
        if req.enabled is not None:
            coord.agent.training_enabled = req.enabled
        if req.greedy is not None:
            coord.agent.greedy = req.greedy
        if req.temperature is not None:
            coord.agent.temperature = float(np.clip(req.temperature, 0.2, 3.0))
        if req.save and not req.reset:
            coord.persist_state(commit_partial=False)
    return {"status": "updated", **coord.training_status()}


@app.post("/api/modulate")
async def manual_modulate(req: ModulateRequest):
    coord = get_coordinator()
    payload = {k: v for k, v in req.model_dump().items() if v is not None}
    coord.snn_engine.update_biophysical_params(payload)
    coord.latest_gemma_state.update(payload)
    coord.latest_gemma_state["neuro_hypothesis"] = (
        "Intervención manual aplicada desde la consola de conferencia."
    )
    coord.persist_state(commit_partial=False)
    return {"status": "updated", "params": payload}


@app.post("/api/dopamine-pulse")
async def trigger_dopamine_pulse(req: DopaminePulseRequest):
    coord = get_coordinator()
    coord.snn_engine.inject_dopamine_pulse(req.valence)
    return {
        "status": "injected",
        "dopamine_level": round(coord.snn_engine.dopamine_level, 3),
    }


@app.websocket("/ws/telemetry")
async def telemetry_websocket(websocket: WebSocket):
    global active_websocket
    coord = get_coordinator()
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
            if not coord.system_running:
                paused_packet = coord.build_paused_packet()
                if paused_packet is not None:
                    await websocket.send_json(paused_packet)
                    await asyncio.sleep(0.25)
                    continue

            packet = await coord.step_simulation_async()
            await websocket.send_json(packet)
            frame_interval = 1.0 / float(max(5, coord.target_fps))
            elapsed = time.perf_counter() - t_start
            await asyncio.sleep(max(0.004, frame_interval - elapsed))
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        if active_websocket is websocket:
            active_websocket = None
