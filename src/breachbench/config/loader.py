"""Parse + validate YAML config into typed models. No network, no keys."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .schema import ExperimentConfig, ModelsRegistry

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EXPERIMENT_PATH = _REPO_ROOT / "config" / "experiment.yaml"
DEFAULT_MODELS_PATH = _REPO_ROOT / "config" / "models.yaml"


def _read_yaml(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")
    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Config file {p} did not parse to a mapping.")
    return data


def load_experiment_config(path: str | Path = DEFAULT_EXPERIMENT_PATH) -> ExperimentConfig:
    return ExperimentConfig.model_validate(_read_yaml(path))


def load_models_registry(path: str | Path = DEFAULT_MODELS_PATH) -> ModelsRegistry:
    return ModelsRegistry.model_validate(_read_yaml(path))
