"""STUB: Judge–human inter-rater reliability (Cohen's / Fleiss κ).

Deliberately NOT implemented (Plan Mode + build step 12 leave this as a hook).
Signatures and the expected gold-set format are fixed here so the analysis wiring
is ready; the body raises until a human-labeled gold set exists.

Expected gold-set format (gold_set/*.csv), one row per human-labeled round:
    transcript_ref, human_verdict           # verdict in the JudgeVerdict enum

The judge labels are joined from rounds.csv on `transcript_ref` (judge_verdict).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ReliabilityResult:
    kappa: float
    n_items: int
    n_raters: int
    method: str  # "cohen" | "fleiss"


def cohen_kappa_judge_vs_human(
    rounds_csv: str | Path, gold_csv: str | Path
) -> ReliabilityResult:  # pragma: no cover - intentional stub
    raise NotImplementedError(
        "Judge–human κ is a stubbed hook. Provide a gold_set CSV "
        "(transcript_ref, human_verdict) and implement the join against "
        "rounds.csv judge_verdict, then compute Cohen's κ."
    )


def fleiss_kappa_panel(
    rounds_csv: str | Path, gold_csv: str | Path
) -> ReliabilityResult:  # pragma: no cover - intentional stub
    raise NotImplementedError(
        "Fleiss κ over a multi-judge panel + human labels is a stubbed hook."
    )
