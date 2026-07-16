"""Load scenario YAML files into validated ScenarioSpec objects."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .schema import ScenarioSpec

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCENARIO_DIR = _REPO_ROOT / "config" / "scenarios"


def _read_yaml(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Scenario file not found: {p}")
    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Scenario file {p} did not parse to a mapping.")
    return data


def load_scenario_file(path: str | Path) -> ScenarioSpec:
    return ScenarioSpec.model_validate(_read_yaml(path))


def load_scenarios(scenario_dir: str | Path = DEFAULT_SCENARIO_DIR) -> dict[str, ScenarioSpec]:
    """Load every *.yaml in the directory, keyed by scenario_id."""
    d = Path(scenario_dir)
    out: dict[str, ScenarioSpec] = {}
    for f in sorted(d.glob("*.yaml")):
        spec = load_scenario_file(f)
        if spec.scenario_id in out:
            raise ValueError(f"Duplicate scenario_id '{spec.scenario_id}' in {f}")
        out[spec.scenario_id] = spec
    return out


def load_scenarios_by_ids(
    ids: list[str], scenario_dir: str | Path = DEFAULT_SCENARIO_DIR
) -> dict[str, ScenarioSpec]:
    """Load only the requested scenario ids (used by the runner grid)."""
    all_scenarios = load_scenarios(scenario_dir)
    missing = [sid for sid in ids if sid not in all_scenarios]
    if missing:
        raise KeyError(f"Scenario ids not found in {scenario_dir}: {missing}")
    return {sid: all_scenarios[sid] for sid in ids}
