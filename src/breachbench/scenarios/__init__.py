"""Scenario/persona definitions, canary generation, and Target rendering."""

from .canary import RenderedTarget, generate_canary, render_target
from .loader import (
    DEFAULT_SCENARIO_DIR,
    load_scenario_file,
    load_scenarios,
    load_scenarios_by_ids,
)
from .schema import CanarySpec, ForbiddenToolSpec, PersonaTemplate, ScenarioSpec

__all__ = [
    "CanarySpec",
    "DEFAULT_SCENARIO_DIR",
    "ForbiddenToolSpec",
    "PersonaTemplate",
    "RenderedTarget",
    "ScenarioSpec",
    "generate_canary",
    "load_scenario_file",
    "load_scenarios",
    "load_scenarios_by_ids",
    "render_target",
]
