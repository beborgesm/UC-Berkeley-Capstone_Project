"""Grid enumeration with the Attacker != Target guard.

The cell key is (target × scenario × attack_vector); the Attacker is a fixed
instrument, not an axis. Any cell whose Target model equals the configured Attacker
model is skipped (and relabeled/recorded), to avoid self-attack confounds.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config.schema import ExperimentConfig
from ..loop.types import Cell


@dataclass(frozen=True)
class GridPlan:
    cells: list[Cell] = field(default_factory=list)
    skipped_self_attack: list[Cell] = field(default_factory=list)


def enumerate_cells(config: ExperimentConfig) -> GridPlan:
    cells: list[Cell] = []
    skipped: list[Cell] = []
    for target in config.targets:
        for scenario_id in config.scenarios:
            for vector in config.vectors:
                cell = Cell(target=target, scenario_id=scenario_id, attack_vector=vector)
                if target == config.attacker:
                    skipped.append(cell)  # Attacker != Target guard
                else:
                    cells.append(cell)
    return GridPlan(cells=cells, skipped_self_attack=skipped)


def enumerate_runs(config: ExperimentConfig) -> list[tuple[Cell, int]]:
    """All (cell, repetition_index) pairs to execute, in deterministic order."""
    plan = enumerate_cells(config)
    return [
        (cell, rep)
        for cell in plan.cells
        for rep in range(config.repetitions)
    ]
