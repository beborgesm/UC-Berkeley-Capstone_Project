"""Load the KM input: run_summary.csv -> per-cell (t_i, δ_i) observations.

Only run_valid == 1 rows are analyzed (invalidated runs are excluded, per §3.3).
Accepts either a run_summary.csv directly or a rounds.csv (which it projects).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ..recording.run_summary import rounds_df_to_run_summary


@dataclass
class CellObservations:
    cell_id: str
    target_vendor: str
    target_model_version: str
    scenario_id: str
    attack_vector: str
    durations: np.ndarray  # t_i in {1..k_max}
    events: np.ndarray  # δ_i in {0,1}

    @property
    def n(self) -> int:
        return int(len(self.durations))

    @property
    def n_events(self) -> int:
        return int(self.events.sum())

    @property
    def n_censored(self) -> int:
        return self.n - self.n_events


def _load_summary_frame(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "event_observed" not in df.columns:
        # A rounds.csv was passed — project it to the per-run summary.
        df = rounds_df_to_run_summary(df)
    return df


def load_cell_observations(path: str | Path) -> list[CellObservations]:
    df = _load_summary_frame(path)
    df = df[df["run_valid"] == 1]
    cells: list[CellObservations] = []
    for cell_id, grp in df.groupby("cell_id"):
        cells.append(
            CellObservations(
                cell_id=str(cell_id),
                target_vendor=str(grp["target_vendor"].iloc[0]),
                target_model_version=str(grp["target_model_version"].iloc[0]),
                scenario_id=str(grp["scenario_id"].iloc[0]),
                attack_vector=str(grp["attack_vector"].iloc[0]),
                durations=grp["duration_rounds"].to_numpy(dtype=float),
                events=grp["event_observed"].to_numpy(dtype=int),
            )
        )
    return cells
