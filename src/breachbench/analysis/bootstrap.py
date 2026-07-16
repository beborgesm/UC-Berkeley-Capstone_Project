"""Bootstrap confidence intervals — the PRIMARY CI (Appendix B).

Resample runs within a cell with replacement (B≈10000), recompute the KM survival
curve and ASR@k_max on each resample, and take percentile bands. Seeded for
reproducibility.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .km import kaplan_meier


@dataclass
class BootstrapResult:
    survival_lower: np.ndarray  # per-round percentile band
    survival_upper: np.ndarray
    asr_kmax_lower: float
    asr_kmax_upper: float
    B: int


def bootstrap_survival(
    durations: np.ndarray,
    events: np.ndarray,
    k_max: int,
    *,
    B: int = 10000,
    alpha: float = 0.05,
    seed: int = 0,
) -> BootstrapResult:
    durations = np.asarray(durations, dtype=float)
    events = np.asarray(events, dtype=int)
    n = len(durations)
    rng = np.random.default_rng(seed)

    survivals = np.empty((B, k_max), dtype=float)
    asr_kmax = np.empty(B, dtype=float)
    for b in range(B):
        idx = rng.integers(0, n, size=n)
        km = kaplan_meier(durations[idx], events[idx], k_max, alpha=alpha)
        survivals[b] = km.survival
        asr_kmax[b] = km.asr_at_kmax

    lo_q, hi_q = 100 * (alpha / 2), 100 * (1 - alpha / 2)
    surv_lower = np.percentile(survivals, lo_q, axis=0)
    surv_upper = np.percentile(survivals, hi_q, axis=0)
    asr_lo = float(np.percentile(asr_kmax, lo_q))
    asr_hi = float(np.percentile(asr_kmax, hi_q))
    return BootstrapResult(
        survival_lower=surv_lower,
        survival_upper=surv_upper,
        asr_kmax_lower=asr_lo,
        asr_kmax_upper=asr_hi,
        B=B,
    )
