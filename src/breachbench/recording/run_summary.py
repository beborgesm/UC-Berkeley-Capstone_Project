"""Derive run_summary.csv (one row per run) — the direct Kaplan–Meier input.

Projection from rounds.csv: filter to `is_terminal_round == 1`, then rename
`run_event_observed -> event_observed`. This rename is the ONLY place an
`event_observed` column exists, so:
  * the raw round file has NO event column (can't be mis-fit), and
  * the KM input has exactly one, unambiguous event column.

lifelines then runs directly on `T = duration_rounds`, `E = event_observed`, with
no reshaping. The three encodings are:
  breach at k*   -> (duration=k*,    event=1, censored=0)
  survived k_max -> (duration=k_max, event=0, censored=1)
  admin/invalid  -> event=0 (run_valid=0 rows should be excluded before fitting)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from .schema import RUN_SUMMARY_COLUMNS

if TYPE_CHECKING:
    from ..loop.types import RunResult


def rounds_df_to_run_summary(rounds: pd.DataFrame) -> pd.DataFrame:
    """Project a rounds.csv DataFrame to the per-run KM summary."""
    terminal = rounds[rounds["is_terminal_round"] == 1].copy()
    # Belt-and-suspenders: if a resumed run ever duplicated a terminal row, keep one
    # per run_id so the KM input is exactly one observation per run.
    terminal = terminal.drop_duplicates(subset="run_id", keep="last")
    terminal = terminal.rename(columns={"run_event_observed": "event_observed"})
    return terminal[list(RUN_SUMMARY_COLUMNS)].reset_index(drop=True)


def run_summary_from_csv(rounds_csv: str | Path) -> pd.DataFrame:
    rounds = pd.read_csv(rounds_csv)
    return rounds_df_to_run_summary(rounds)


def write_run_summary_csv(rounds_csv: str | Path, out_csv: str | Path) -> Path:
    summary = run_summary_from_csv(rounds_csv)
    out = Path(out_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out, index=False)
    return out


def run_result_to_summary_row(result: "RunResult") -> dict[str, Any]:
    """Build a run_summary row straight from a RunResult (bypasses the CSV round
    trip; used in tests and by the runner as a convenience)."""
    return {
        "run_id": result.run_id,
        "cell_id": result.cell.cell_id(),
        "target_vendor": result.cell.target.vendor.value,
        "target_model_version": result.cell.target.model_version,
        "scenario_id": result.cell.scenario_id,
        "breach_type_targeted": "",  # filled by the caller if needed
        "attack_vector": result.cell.attack_vector.value,
        "repetition_index": result.repetition_index,
        "duration_rounds": result.duration_rounds,
        "event_observed": result.event_observed,  # <- run-level event, renamed
        "censored": result.censored,
        "termination_reason": result.termination_reason.value,
        "run_valid": result.run_valid,
    }
