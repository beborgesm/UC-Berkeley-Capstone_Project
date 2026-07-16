"""ASR@k_max tables and per-vector heatmap matrices (Appendix B reporting).

ASR@k = 1 − Ŝ(k); the headline per cell is ASR@k_max, computed from the KM curve
(not a naive breach fraction), so censoring is handled correctly.
"""

from __future__ import annotations

import pandas as pd

from .bootstrap import bootstrap_survival
from .km import kaplan_meier
from .loader import CellObservations


def asr_table(
    cells: list[CellObservations],
    k_max: int,
    *,
    bootstrap_B: int = 0,
    seed: int = 0,
) -> pd.DataFrame:
    """Long-format per-cell ASR@k_max with N and censoring counts. If bootstrap_B>0,
    include bootstrap CI bounds."""
    rows = []
    for c in cells:
        km = kaplan_meier(c.durations, c.events, k_max)
        row = {
            "cell_id": c.cell_id,
            "target_vendor": c.target_vendor,
            "target_model_version": c.target_model_version,
            "scenario_id": c.scenario_id,
            "attack_vector": c.attack_vector,
            "n": c.n,
            "n_events": c.n_events,
            "n_censored": c.n_censored,
            "asr_at_kmax": km.asr_at_kmax,
            "survival_at_kmax": km.survival_at_kmax,
        }
        if bootstrap_B > 0 and c.n > 0:
            bs = bootstrap_survival(c.durations, c.events, k_max, B=bootstrap_B, seed=seed)
            row["asr_kmax_ci_lower"] = bs.asr_kmax_lower
            row["asr_kmax_ci_upper"] = bs.asr_kmax_upper
        rows.append(row)
    return pd.DataFrame(rows)


def asr_heatmap_matrix(table: pd.DataFrame, scenario_id: str) -> pd.DataFrame:
    """Vectors (rows) × models (cols) ASR@k_max matrix for one scenario."""
    sub = table[table["scenario_id"] == scenario_id]
    return sub.pivot_table(
        index="attack_vector",
        columns="target_model_version",
        values="asr_at_kmax",
        aggfunc="mean",
    )
