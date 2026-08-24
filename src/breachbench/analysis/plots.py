"""Publication-quality figures for the report: Kaplan–Meier survival curves and
ASR@k_max heatmaps.

Design choices (per the dataviz method):
- Models are a CATEGORICAL identity → fixed-order, colorblind-safe **Okabe–Ito** hues,
  assigned to models consistently across every panel (never cycled per-panel).
- ASR is a MAGNITUDE over two categorical axes → a **single-hue sequential** heatmap
  (light→dark red = more broken), with the value printed in every cell so it reads
  even in grayscale / for CVD.
- Recessive axes + gridlines, thin marks, a legend whenever ≥2 models are shown.

Matplotlib only (ships with lifelines); Agg backend so it renders headless.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .asr import asr_heatmap_matrix
from .bootstrap import bootstrap_survival
from .km import kaplan_meier
from .labels import prettify_model
from .loader import CellObservations

# Okabe–Ito categorical palette (colorblind-safe), minus low-contrast yellow/black.
_OKABE_ITO = ["#0072B2", "#D55E00", "#009E73", "#E69F00", "#CC79A7", "#56B4E9"]

_INK = "#222222"
_MUTED = "#888888"


def _apply_style() -> None:
    plt.rcParams.update({
        "figure.dpi": 130,
        "savefig.dpi": 150,
        "font.size": 11,
        "axes.edgecolor": _MUTED,
        "axes.linewidth": 0.8,
        "axes.grid": True,
        "grid.color": "#E6E6E6",
        "grid.linewidth": 0.7,
        "axes.axisbelow": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "text.color": _INK,
        "axes.labelcolor": _INK,
        "xtick.color": _MUTED,
        "ytick.color": _MUTED,
    })


def _model_colors(models: list[str]) -> dict[str, str]:
    return {m: _OKABE_ITO[i % len(_OKABE_ITO)] for i, m in enumerate(sorted(models))}


def _km_step(cell: CellObservations, k_max: int, bootstrap_B: int, seed: int = 0):
    """Return (x, S, lo, hi) with a leading (0, 1) point for a proper step plot."""
    km = kaplan_meier(cell.durations, cell.events, k_max)
    x = np.concatenate([[0], km.k])
    s = np.concatenate([[1.0], km.survival])
    if bootstrap_B > 0 and cell.n > 1:
        bs = bootstrap_survival(cell.durations, cell.events, k_max, B=bootstrap_B, seed=seed)
        lo = np.concatenate([[1.0], bs.survival_lower])
        hi = np.concatenate([[1.0], bs.survival_upper])
    else:
        lo = hi = None
    return x, s, lo, hi


def plot_km_survival(
    cells: list[CellObservations], scenario_id: str, k_max: int, out_path: str | Path,
    *, bootstrap_B: int = 1000,
) -> Path | None:
    """Small multiples: one panel per attack vector; one KM survival curve per model
    (with bootstrap CI band). Returns the written path, or None if no data."""
    sub = [c for c in cells if c.scenario_id == scenario_id]
    if not sub:
        return None
    _apply_style()
    vectors = sorted({c.attack_vector for c in sub})
    models = sorted({prettify_model(c.target_model_version) for c in sub})
    colors = _model_colors(models)

    n = len(vectors)
    ncol = min(n, 2)
    nrow = (n + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(6.2 * ncol, 3.6 * nrow), squeeze=False)
    for idx, vector in enumerate(vectors):
        ax = axes[idx // ncol][idx % ncol]
        for c in [c for c in sub if c.attack_vector == vector]:
            m = prettify_model(c.target_model_version)
            x, s, lo, hi = _km_step(c, k_max, bootstrap_B)
            ax.step(x, s, where="post", color=colors[m], lw=2, label=f"{m} (n={c.n})")
            if lo is not None:
                ax.fill_between(x, lo, hi, step="post", color=colors[m], alpha=0.15, lw=0)
        ax.set_title(vector, fontsize=11, color=_INK)
        ax.set_xlim(0, k_max)
        ax.set_ylim(-0.02, 1.02)
        ax.set_xlabel("round k")
        ax.set_ylabel("Ŝ(k)  survival")
        ax.legend(fontsize=8, frameon=False, loc="lower left")
    for j in range(n, nrow * ncol):
        axes[j // ncol][j % ncol].axis("off")
    fig.suptitle(f"Kaplan–Meier survival — {scenario_id}", fontsize=13, y=1.0)
    fig.tight_layout()
    out = Path(out_path)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_asr_heatmap(asr_table, scenario_id: str, out_path: str | Path) -> Path | None:
    """Vectors (rows) × models (cols) ASR@k_max heatmap, single-hue sequential, with
    the value printed in every cell."""
    mat = asr_heatmap_matrix(asr_table, scenario_id)
    if mat.empty:
        return None
    _apply_style()
    mat = mat.rename(columns=prettify_model)
    data = mat.to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(1.6 * len(mat.columns) + 2.5, 0.7 * len(mat.index) + 2))
    im = ax.imshow(data, cmap="Reds", vmin=0.0, vmax=1.0, aspect="auto")
    ax.set_xticks(range(len(mat.columns)), mat.columns, rotation=20, ha="right")
    ax.set_yticks(range(len(mat.index)), mat.index)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i, j]
            if np.isnan(v):
                continue
            ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                    color="white" if v > 0.55 else _INK, fontsize=10, fontweight="bold")
    ax.grid(False)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("ASR@k_max", color=_INK)
    ax.set_title(f"Attack success rate (ASR@k_max) — {scenario_id}", fontsize=12, color=_INK)
    fig.tight_layout()
    out = Path(out_path)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def generate_figures(
    cells: list[CellObservations], asr_table, k_max: int, out_dir: str | Path,
    *, bootstrap_B: int = 1000,
) -> list[Path]:
    """Write KM + heatmap figures for every scenario present. Returns the paths."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for scenario_id in sorted({c.scenario_id for c in cells}):
        km = plot_km_survival(cells, scenario_id, k_max, out_dir / f"km_{scenario_id}.png",
                              bootstrap_B=bootstrap_B)
        heat = plot_asr_heatmap(asr_table, scenario_id, out_dir / f"asr_heatmap_{scenario_id}.png")
        written.extend(p for p in (km, heat) if p is not None)
    return written


def summary_table_markdown(asr_table) -> str:
    """A clean per-cell ASR@k_max table (with CI, N, censoring) as markdown."""
    cols = ["scenario_id", "attack_vector", "target_model_version", "n", "n_events",
            "n_censored", "asr_at_kmax"]
    has_ci = "asr_kmax_ci_lower" in asr_table.columns
    lines = ["| scenario | vector | model | N | breaches | censored | ASR@k_max"
             + (" | 95% CI |" if has_ci else " |"),
             "|---|---|---|---|---|---|---" + ("|---|" if has_ci else "|")]
    t = asr_table.sort_values(["scenario_id", "attack_vector", "target_model_version"])
    for _, r in t.iterrows():
        ci = ""
        if has_ci:
            ci = f" [{r['asr_kmax_ci_lower']:.2f}, {r['asr_kmax_ci_upper']:.2f}] |"
        lines.append(
            f"| {r['scenario_id']} | {r['attack_vector']} | {prettify_model(r['target_model_version'])} "
            f"| {int(r['n'])} | {int(r['n_events'])} | {int(r['n_censored'])} "
            f"| {r['asr_at_kmax']:.2f} |{ci}"
        )
    return "\n".join(lines)
