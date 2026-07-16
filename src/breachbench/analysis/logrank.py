"""Between-model log-rank test for PRE-REGISTERED pairs only (Appendix B).

Per round k (matched scenario × vector):
  E_{A,k} = d_k · n_{A,k} / n_k
  V_k     = d_k (n_k − d_k) n_{A,k} n_{B,k} / (n_k^2 (n_k − 1))
  χ²      = (Σ_k (d_{A,k} − E_{A,k}))^2 / Σ_k V_k   ~ χ²₁

Non-significance ≠ equivalence; small-N results are flagged underpowered.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Below this per-group N the test is flagged underpowered (advisory only).
UNDERPOWERED_N = 20


@dataclass
class LogrankResult:
    chi2: float
    p_value: float
    n_a: int
    n_b: int
    underpowered: bool

    def summary(self) -> str:
        flag = " [UNDERPOWERED]" if self.underpowered else ""
        return f"chi2={self.chi2:.3f} p={self.p_value:.4f} n_a={self.n_a} n_b={self.n_b}{flag}"


def _p_from_chi2(chi2: float) -> float:
    try:
        from scipy.stats import chi2 as chi2_dist

        return float(chi2_dist.sf(chi2, df=1))
    except Exception:
        # Fallback: survival of chi2_1 = erfc(sqrt(chi2/2)); use math.erfc.
        import math

        return math.erfc(math.sqrt(max(chi2, 0.0) / 2.0))


def logrank_test(
    dur_a: np.ndarray,
    ev_a: np.ndarray,
    dur_b: np.ndarray,
    ev_b: np.ndarray,
    k_max: int,
) -> LogrankResult:
    dur_a = np.asarray(dur_a, float); ev_a = np.asarray(ev_a, int)
    dur_b = np.asarray(dur_b, float); ev_b = np.asarray(ev_b, int)
    n_a, n_b = len(dur_a), len(dur_b)

    obs_minus_exp = 0.0
    var_sum = 0.0
    for k in range(1, k_max + 1):
        n_ak = int(np.sum(dur_a >= k))
        n_bk = int(np.sum(dur_b >= k))
        n_k = n_ak + n_bk
        d_ak = int(np.sum((dur_a == k) & (ev_a == 1)))
        d_bk = int(np.sum((dur_b == k) & (ev_b == 1)))
        d_k = d_ak + d_bk
        if n_k <= 1 or d_k == 0:
            continue
        e_ak = d_k * n_ak / n_k
        v_k = d_k * (n_k - d_k) * n_ak * n_bk / (n_k ** 2 * (n_k - 1))
        obs_minus_exp += d_ak - e_ak
        var_sum += v_k

    chi2 = (obs_minus_exp ** 2 / var_sum) if var_sum > 0 else 0.0
    p = _p_from_chi2(chi2)
    underpowered = min(n_a, n_b) < UNDERPOWERED_N
    return LogrankResult(chi2=chi2, p_value=p, n_a=n_a, n_b=n_b, underpowered=underpowered)
