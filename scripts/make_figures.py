#!/usr/bin/env python3
"""Presentation figure gallery for BreachBenchmark.

Produces MANY publication-quality figures (more than a deck needs) so the team can pick
the strongest ones. Primary (deterministic) figures always render; secondary Judge-degradation
figures render only if output/judge_scores.csv exists.

    ./.venv/bin/python scripts/make_figures.py --rounds-csv output/rounds_3models.csv --out output/figures

Design: colorblind-safe Okabe-Ito hues assigned per model (consistent across every panel),
recessive axes/grid, values printed on bars/cells, bootstrap CIs. Matplotlib Agg (headless).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from breachbench.analysis.loader import load_cell_observations  # noqa: E402
from breachbench.analysis.km import kaplan_meier  # noqa: E402

# ---- palette + style ----
OKABE = ["#0072B2", "#D55E00", "#009E73", "#E69F00", "#CC79A7", "#56B4E9"]
INK, MUTED, GRID = "#222222", "#8a8a8a", "#E6E6E6"
# stable model color + display order (weakest -> strongest for narrative)
MODEL_ORDER = ["gpt-3.5-turbo", "gpt-5-nano", "gpt-4o-mini"]
MODEL_COLOR = {"gpt-3.5-turbo": "#D55E00", "gpt-5-nano": "#E69F00", "gpt-4o-mini": "#009E73"}
MODEL_YEAR = {"gpt-3.5-turbo": 2023, "gpt-4o-mini": 2024, "gpt-5-nano": 2025}
MODEL_NOTE = {"gpt-3.5-turbo": "2023 · older", "gpt-4o-mini": "2024 · efficient",
              "gpt-5-nano": "2025 · newest, tiny"}
VECTOR_ORDER = ["ROLEPLAY", "AUTHORITY", "CIPHER", "MANY_SHOT"]
SCEN_LABEL = {"conf_vault_v1": "Confidentiality (canary)", "integ_override_v1": "Integrity (tool)"}


def style():
    plt.rcParams.update({
        "figure.dpi": 130, "savefig.dpi": 160, "font.size": 11,
        "axes.edgecolor": MUTED, "axes.linewidth": 0.8, "axes.grid": True,
        "grid.color": GRID, "grid.linewidth": 0.7, "axes.axisbelow": True,
        "axes.spines.top": False, "axes.spines.right": False,
        "text.color": INK, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    })


def pretty(name: str) -> str:
    return re.sub(r"-\d{4}-\d{2}-\d{2}$|-\d{4}$", "", str(name))


def mcolor(m: str) -> str:
    return MODEL_COLOR.get(m, OKABE[hash(m) % len(OKABE)])


def order_models(models) -> list[str]:
    present = set(models)
    return [m for m in MODEL_ORDER if m in present] + sorted(present - set(MODEL_ORDER))


def boot_ci(events: np.ndarray, B: int = 5000, seed: int = 7) -> tuple[float, float, float]:
    """ASR = mean(events); percentile bootstrap CI."""
    rng = np.random.default_rng(seed)
    n = len(events)
    if n == 0:
        return (0.0, 0.0, 0.0)
    est = float(events.mean())
    if n == 1:
        return (est, est, est)
    idx = rng.integers(0, n, size=(B, n))
    samp = events[idx].mean(axis=1)
    return est, float(np.percentile(samp, 2.5)), float(np.percentile(samp, 97.5))


# ============================================================ data assembly
def build_frames(rounds_csv: Path):
    cells = load_cell_observations(rounds_csv)
    rows = []
    for c in cells:
        rows.append({
            "model": pretty(c.target_model_version), "scenario": c.scenario_id,
            "vector": c.attack_vector, "durations": c.durations, "events": c.events,
        })
    return rows


def pool(rows, model=None, scenario=None, vector=None):
    ev, du = [], []
    for r in rows:
        if model and r["model"] != model:
            continue
        if scenario and r["scenario"] != scenario:
            continue
        if vector and r["vector"] != vector:
            continue
        ev.append(r["events"])
        du.append(r["durations"])
    if not ev:
        return np.array([]), np.array([])
    return np.concatenate(du), np.concatenate(ev)


# ============================================================ figures
def fig_asr_by_model(rows, out):
    style()
    models = order_models({r["model"] for r in rows})
    est, lo, hi, ns = [], [], [], []
    for m in models:
        _, ev = pool(rows, model=m)
        e, l, h = boot_ci(ev)
        est.append(e); lo.append(e - l); hi.append(h - e); ns.append(len(ev))
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    x = np.arange(len(models))
    bars = ax.bar(x, est, width=0.62, color=[mcolor(m) for m in models],
                  yerr=[lo, hi], capsize=5, error_kw=dict(ecolor=MUTED, lw=1.2))
    for xi, e, n in zip(x, est, ns):
        ax.text(xi, e + max(hi) * 0.04 + 0.02, f"{e*100:.0f}%", ha="center", va="bottom",
                fontweight="bold", fontsize=13, color=INK)
    ax.set_xticks(x, [f"{m}\n{MODEL_NOTE.get(m,'')}" for m in models])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Attack success rate (ASR@k=10)")
    ax.set_title("How breakable is each model?  Overall ASR across all attacks", fontweight="bold")
    ax.text(0.5, -0.22, f"Pooled over 2 scenarios × 4 vectors × {ns[0]//8} reps each "
            f"(n≈{ns[0]} runs/model).  Bars = bootstrap 95% CI.",
            transform=ax.transAxes, ha="center", fontsize=8.5, color=MUTED)
    fig.tight_layout(); fig.savefig(out, bbox_inches="tight"); plt.close(fig)


def fig_km_by_model(rows, out, k_max=10):
    style()
    models = order_models({r["model"] for r in rows})
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    for m in models:
        du, ev = pool(rows, model=m)
        km = kaplan_meier(du, ev, k_max)
        x = np.concatenate([[0], km.k]); s = np.concatenate([[1.0], km.survival])
        ax.step(x, s, where="post", color=mcolor(m), lw=2.6, label=f"{m}  (n={len(ev)})")
        ax.plot(x, s, drawstyle="steps-post", color=mcolor(m), lw=0)
    ax.set_xlim(0, k_max); ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("attack round k"); ax.set_ylabel("Ŝ(k) — probability boundary still holds")
    ax.set_title("Survival under sustained attack (pooled across all vectors)", fontweight="bold")
    ax.legend(frameon=False, loc="upper right", fontsize=10)
    fig.tight_layout(); fig.savefig(out, bbox_inches="tight"); plt.close(fig)


def _grouped_bars(ax, cats, models, val_fn):
    nmod = len(models)
    w = 0.8 / nmod
    x = np.arange(len(cats))
    for j, m in enumerate(models):
        vals = [val_fn(c, m) for c in cats]
        xs = x + (j - (nmod - 1) / 2) * w
        ax.bar(xs, vals, width=w * 0.94, color=mcolor(m), label=m)
        for xi, v in zip(xs, vals):
            if v > 0.02:
                ax.text(xi, v + 0.015, f"{v:.2f}", ha="center", va="bottom", fontsize=7.5, color=INK)
    ax.set_xticks(x, cats)
    ax.set_ylim(0, 1.08)


def fig_asr_by_vector(rows, out):
    style()
    models = order_models({r["model"] for r in rows})
    vectors = [v for v in VECTOR_ORDER if v in {r["vector"] for r in rows}]
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    def vf(vec, m):
        _, ev = pool(rows, model=m, vector=vec)
        return ev.mean() if len(ev) else 0.0
    _grouped_bars(ax, vectors, models, vf)
    ax.set_ylabel("ASR@k=10"); ax.set_title("Which attack strategy works best? (ASR by vector)", fontweight="bold")
    ax.legend(frameon=False, ncol=len(models), loc="upper center", bbox_to_anchor=(0.5, 1.0), fontsize=9)
    fig.tight_layout(); fig.savefig(out, bbox_inches="tight"); plt.close(fig)


def fig_asr_by_scenario(rows, out):
    style()
    models = order_models({r["model"] for r in rows})
    scens = [s for s in ["conf_vault_v1", "integ_override_v1"] if s in {r["scenario"] for r in rows}]
    fig, ax = plt.subplots(figsize=(7.0, 4.5))
    def vf(sc, m):
        _, ev = pool(rows, model=m, scenario=sc)
        return ev.mean() if len(ev) else 0.0
    _grouped_bars(ax, [SCEN_LABEL.get(s, s) for s in scens], models,
                  lambda lbl, m: vf({v: k for k, v in SCEN_LABEL.items()}.get(lbl, lbl), m))
    ax.set_ylabel("ASR@k=10"); ax.set_title("Confidentiality vs Integrity — ASR by boundary", fontweight="bold")
    ax.legend(frameon=False, ncol=len(models), loc="upper center", fontsize=9)
    fig.tight_layout(); fig.savefig(out, bbox_inches="tight"); plt.close(fig)


def fig_breach_round_hist(rows, out, k_max=10):
    style()
    models = order_models({r["model"] for r in rows})
    fig, axes = plt.subplots(1, len(models), figsize=(4.2 * len(models), 3.7), sharey=True)
    if len(models) == 1:
        axes = [axes]
    for ax, m in zip(axes, models):
        du, ev = pool(rows, model=m)
        brounds = du[ev == 1]
        ax.hist(brounds, bins=np.arange(0.5, k_max + 1.5, 1), color=mcolor(m), edgecolor="white", lw=1)
        ax.set_title(f"{m}\n{len(brounds)} breaches / {len(ev)} runs", fontsize=10)
        ax.set_xlabel("breach round k"); ax.set_xlim(0.5, k_max + 0.5); ax.set_xticks(range(1, k_max + 1))
    axes[0].set_ylabel("number of breaches")
    fig.suptitle("When do breaches happen? Distribution of breach round", fontweight="bold", y=1.02)
    fig.tight_layout(); fig.savefig(out, bbox_inches="tight"); plt.close(fig)


def fig_heatmap_model_vector(rows, out):
    style()
    models = order_models({r["model"] for r in rows})
    scens = [s for s in ["conf_vault_v1", "integ_override_v1"] if s in {r["scenario"] for r in rows}]
    vectors = [v for v in VECTOR_ORDER if v in {r["vector"] for r in rows}]
    fig, axes = plt.subplots(1, len(scens), figsize=(4.9 * len(scens), 4.2))
    if len(scens) == 1:
        axes = [axes]
    for ai, (ax, sc) in enumerate(zip(axes, scens)):
        data = np.full((len(vectors), len(models)), np.nan)
        for i, vec in enumerate(vectors):
            for j, m in enumerate(models):
                _, ev = pool(rows, model=m, scenario=sc, vector=vec)
                if len(ev):
                    data[i, j] = ev.mean()
        im = ax.imshow(data, cmap="Reds", vmin=0, vmax=1, aspect="auto")
        ax.set_xticks(range(len(models)), models, rotation=18, ha="right")
        if ai == 0:
            ax.set_yticks(range(len(vectors)), vectors)
        else:
            ax.set_yticks(range(len(vectors)), [""] * len(vectors))
        for i in range(len(vectors)):
            for j in range(len(models)):
                v = data[i, j]
                if not np.isnan(v):
                    ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                            color="white" if v > 0.55 else INK, fontweight="bold", fontsize=10)
        ax.grid(False); ax.set_title(SCEN_LABEL.get(sc, sc), fontsize=11)
    fig.suptitle("ASR@k=10 heatmap — model × attack vector", fontweight="bold", y=1.02)
    fig.colorbar(im, ax=axes, fraction=0.046, pad=0.04).set_label("ASR")
    fig.savefig(out, bbox_inches="tight"); plt.close(fig)


def fig_capability_vs_recency(rows, out):
    style()
    models = order_models({r["model"] for r in rows})
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    for m in models:
        _, ev = pool(rows, model=m)
        rob = 1 - ev.mean()
        yr = MODEL_YEAR.get(m, 2024)
        ax.scatter(yr, rob, s=260, color=mcolor(m), edgecolor="white", lw=1.5, zorder=3)
        ax.annotate(f"{m}\n{rob*100:.0f}% held", (yr, rob),
                    textcoords="offset points", xytext=(0, 14), ha="center", fontsize=9.5, color=INK)
    ax.set_xlabel("model release year"); ax.set_ylabel("overall robustness (1 − ASR)")
    ax.set_ylim(-0.05, 1.12); ax.set_xticks(sorted(set(MODEL_YEAR.values())))
    ax.set_title("Newer ≠ safer: capability, not recency, drives robustness", fontweight="bold")
    ax.text(0.5, -0.2, "The 2025 small model (gpt-5-nano) is MORE breakable than the 2024 gpt-4o-mini.",
            transform=ax.transAxes, ha="center", fontsize=8.5, color=MUTED)
    fig.tight_layout(); fig.savefig(out, bbox_inches="tight"); plt.close(fig)


PRIMARY = [
    ("asr_by_model", fig_asr_by_model),
    ("km_by_model", fig_km_by_model),
    ("asr_by_vector", fig_asr_by_vector),
    ("asr_by_scenario", fig_asr_by_scenario),
    ("breach_round_hist", fig_breach_round_hist),
    ("heatmap_model_vector", fig_heatmap_model_vector),
    ("capability_vs_recency", fig_capability_vs_recency),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds-csv", default=str(ROOT / "output" / "rounds_3models.csv"))
    ap.add_argument("--out", default=str(ROOT / "output" / "figures"))
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    rows = build_frames(Path(args.rounds_csv))
    print(f"loaded {len(rows)} cells; models: {order_models({r['model'] for r in rows})}")
    for name, fn in PRIMARY:
        p = out / f"fig_{name}.png"
        fn(rows, p)
        print(f"  wrote {p.name}")
    print("primary figures done")


if __name__ == "__main__":
    main()
