"""Kaplan–Meier survival on discrete rounds, with Greenwood variance and a
complementary log–log (cloglog) confidence interval (Appendix B).

Discrete-time formulas (t_i ∈ {1..k_max}, ties expected):
  n_k = #{t_i >= k}                       (at risk into round k)
  d_k = #{t_i == k and δ_i == 1}          (breaches at exactly k)
  Ŝ(k) = ∏_{j<=k} (1 − d_j/n_j)
  Var[Ŝ(k)] = Ŝ(k)^2 · Σ_{j<=k} d_j / (n_j (n_j − d_j))      (Greenwood)
  cloglog CI: Ŝ(k)^{exp(± z · sqrt(Var[Ĉ(k)]))}, Ĉ=log(−log Ŝ),
             Var[Ĉ] = Var[Ŝ] / (Ŝ · log Ŝ)^2

Plain Wald on Ŝ is intentionally NOT used (it exits [0,1] at the tails).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _z_value(alpha: float) -> float:
    try:
        from scipy.stats import norm

        return float(norm.ppf(1 - alpha / 2))
    except Exception:
        return 1.959963984540054 if abs(alpha - 0.05) < 1e-9 else 1.959963984540054


@dataclass
class KMResult:
    k: np.ndarray  # rounds 1..k_max
    survival: np.ndarray  # Ŝ(k)
    greenwood_var: np.ndarray
    ci_lower: np.ndarray  # cloglog band
    ci_upper: np.ndarray
    n_at_risk: np.ndarray
    n_events: np.ndarray
    n: int
    n_censored: int

    @property
    def asr(self) -> np.ndarray:
        return 1.0 - self.survival

    @property
    def asr_at_kmax(self) -> float:
        return float(1.0 - self.survival[-1])

    @property
    def survival_at_kmax(self) -> float:
        return float(self.survival[-1])


def kaplan_meier(
    durations: np.ndarray, events: np.ndarray, k_max: int, *, alpha: float = 0.05
) -> KMResult:
    durations = np.asarray(durations, dtype=float)
    events = np.asarray(events, dtype=int)
    n = int(len(durations))
    z = _z_value(alpha)

    ks = np.arange(1, k_max + 1)
    survival = np.ones(k_max, dtype=float)
    greenwood = np.zeros(k_max, dtype=float)
    n_at_risk = np.zeros(k_max, dtype=int)
    n_events_k = np.zeros(k_max, dtype=int)

    s = 1.0
    cum_var_term = 0.0  # Σ d_j / (n_j (n_j − d_j))
    for i, k in enumerate(ks):
        n_k = int(np.sum(durations >= k))
        d_k = int(np.sum((durations == k) & (events == 1)))
        n_at_risk[i] = n_k
        n_events_k[i] = d_k
        if n_k > 0 and d_k > 0:
            s *= 1.0 - d_k / n_k
            if n_k - d_k > 0:
                cum_var_term += d_k / (n_k * (n_k - d_k))
        survival[i] = s
        greenwood[i] = (s ** 2) * cum_var_term

    ci_lower, ci_upper = _cloglog_ci(survival, greenwood, z)

    return KMResult(
        k=ks,
        survival=survival,
        greenwood_var=greenwood,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        n_at_risk=n_at_risk,
        n_events=n_events_k,
        n=n,
        n_censored=n - int(events.sum()),
    )


def _cloglog_ci(
    survival: np.ndarray, var: np.ndarray, z: float
) -> tuple[np.ndarray, np.ndarray]:
    lower = survival.copy()
    upper = survival.copy()
    for i, (s, v) in enumerate(zip(survival, var)):
        # cloglog is undefined at S in {0,1} or with zero variance -> degenerate band.
        if s <= 0.0 or s >= 1.0 or v <= 0.0:
            lower[i] = s
            upper[i] = s
            continue
        log_s = np.log(s)
        var_c = v / (s * log_s) ** 2
        half = z * np.sqrt(var_c)
        # S^{exp(+half)} and S^{exp(-half)}; exp(+half) gives the LOWER survival.
        lo = s ** np.exp(half)
        hi = s ** np.exp(-half)
        lower[i] = min(lo, hi)
        upper[i] = max(lo, hi)
    return np.clip(lower, 0.0, 1.0), np.clip(upper, 0.0, 1.0)
