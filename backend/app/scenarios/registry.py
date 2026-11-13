"""Declarative JSON scenario registry supporting drop-in .cfg/.wad configs (OCP)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from ..core.interfaces import ActionSpec, ScenarioConfig

_DEFAULT_CONFIGS_DIR = Path(__file__).resolve().parent / "configs"


class ScenarioRegistry:
    """Discovers and validates declarative scenario configurations."""

    def __init__(self, configs_dir: str | Path | None = None):
        self._configs_dir = Path(configs_dir) if configs_dir else _DEFAULT_CONFIGS_DIR
        self._scenarios: dict[str, ScenarioConfig] = {}
        self.reload()

    def reload(self) -> None:
        self._scenarios.clear()
        if not self._configs_dir.exists():
            return
        for path in sorted(self._configs_dir.glob("*.json")):
            cfg = self._load_file(path)
            self._scenarios[cfg.id] = cfg

    @staticmethod
    def _load_file(path: Path) -> ScenarioConfig:
        with path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
        actions = [
            ActionSpec(
                name=str(item["name"]),
                label=str(item.get("label", item["name"])),
                buttons=[int(b) for b in item["buttons"]],
            )
            for item in raw["actions"]
        ]
        return ScenarioConfig(
            id=str(raw["id"]),
            name=str(raw.get("name", raw["id"])),
            description=str(raw.get("description", "")),
            cfg_file=str(raw["cfg_file"]),
            buttons=[str(b) for b in raw["buttons"]],
            actions=actions,
            game_variables=[str(v) for v in raw.get("game_variables", ["AMMO2", "HEALTH"])],
            episode_timeout=int(raw.get("episode_timeout", 900)),
            default_skill=int(raw.get("default_skill", 3)),
            ammo_max=float(raw.get("ammo_max", 26.0)),
            reward_shaper=str(raw.get("reward_shaper", "combat")),
            is_combat=bool(raw.get("is_combat", True)),
            custom_cfg_path=raw.get("custom_cfg_path"),
            custom_wad_path=raw.get("custom_wad_path"),
        )

    def register(self, config: ScenarioConfig) -> None:
        """Registers a ScenarioConfig programmatically at runtime."""
        self._scenarios[config.id] = config

    def register_json(self, json_path: str | Path) -> ScenarioConfig:
        """Loads and registers an external scenario JSON file."""
        cfg = self._load_file(Path(json_path))
        self._scenarios[cfg.id] = cfg
        return cfg

    def get(self, scenario_id: str) -> ScenarioConfig:
        if scenario_id not in self._scenarios:
            available = ", ".join(sorted(self._scenarios))
            raise KeyError(
                f"Escenario '{scenario_id}' no registrado. Disponibles: [{available}]"
            )
        return self._scenarios[scenario_id]

    def list_ids(self) -> list[str]:
        return list(self._scenarios.keys())

    def list_metadata(self) -> list[dict]:
        return [
            {
                "id": cfg.id,
                "name": cfg.name,
                "description": cfg.description,
                "cfg_file": cfg.cfg_file,
                "n_actions": len(cfg.actions),
                "actions": [a.name for a in cfg.actions],
                "is_combat": cfg.is_combat,
                "default_skill": cfg.default_skill,
                "ammo_max": cfg.ammo_max,
            }
            for cfg in self._scenarios.values()
        ]


def resolve_cfg_path(cfg: ScenarioConfig, scenarios_path: str) -> str:
    """Resolves custom or built-in ViZDoom .cfg file path."""
    if cfg.custom_cfg_path and os.path.exists(cfg.custom_cfg_path):
        return cfg.custom_cfg_path
    if os.path.isabs(cfg.cfg_file) and os.path.exists(cfg.cfg_file):
        return cfg.cfg_file
    return os.path.join(scenarios_path, cfg.cfg_file)
