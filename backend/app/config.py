import os
from pydantic import BaseModel


class BioConfig(BaseModel):
    connectome_path: str = os.getenv("CONNECTOME_PATH", "data/flywire_subconnectome.npz")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "gemma3:4b")
    default_scenario: str = os.getenv("DEFAULT_SCENARIO", "defend_the_center")
    checkpoint_dir: str = os.getenv("CHECKPOINT_DIR", "checkpoints")
    target_fps: int = int(os.getenv("TARGET_FPS", "30"))
    substeps_per_frame: int = 4
    v_rest: float = -52.0
    v_thresh: float = -45.0
    v_reset: float = -52.0
    tau_m: float = 20.0
    tau_syn: float = 5.0
    dopamine_lr: float = 0.008
    sensory_gain: float = 18.0
    noise_std: float = 0.8


settings = BioConfig()
