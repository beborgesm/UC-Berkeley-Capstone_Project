#!/usr/bin/env python3
"""SECONDARY analysis figures: LLM-Judge qualitative degradation.

Reads output/judge_scores.csv (produced by judge_transcripts.py) joined to rounds.csv and
renders the Judge-degradation figures. The Judge is SECONDARY and non-authoritative — it
scores persona/refusal degradation only and NEVER defines a breach. These figures illustrate
that qualitative axis and its (non-causal) concordance with the deterministic breaches.

    ./.venv/bin/python scripts/make_judge_figures.py

Robust to a PARTIAL judge pass — it renders whatever scores exist and prints coverage.
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

INK, MUTED, GRID = "#222222", "#8a8a8a", "#E6E6E6"
MODEL_ORDER = ["gpt-3.5-turbo", "gpt-5-nano", "gpt-4o-mini"]
VERDICTS = ["NO_DEGRADATION", "WEAK_REFUSAL", "PERSONA_BREAK"]
VCOLOR = {"NO_DEGRADATION": "#009E73", "WEAK_REFUSAL": "#E69F00", "PERSONA_BREAK": "#D55E00"}
VLABEL = {"NO_DEGRADATION": "No degradation", "WEAK_REFUSAL": "Weak refusal", "PERSONA_BREAK": "Persona break"}
MCOLOR = {"gpt-3.5-turbo": "#D55E00", "gpt-5-nano": "#E69F00", "gpt-4o-mini": "#009E73"}


def style():
    plt.rcParams.update({
        "figure.dpi": 130, "savefig.dpi": 160, "font.size": 11,
        "axes.edgecolor": MUTED, "axes.linewidth": 0.8, "axes.grid": True,
        "grid.color": GRID, "grid.linewidth": 0.7, "axes.axisbelow": True,
        "axes.spines.top": False, "axes.spines.right": False,
        "text.color": INK, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    })


def pretty(s):
    return re.sub(r"-\d{4}-\d{2}-\d{2}$|-\d{4}$", "", str(s))


def order_models(models):
    present = set(models)
    return [m for m in MODEL_ORDER if m in present] + sorted(present - set(MODEL_ORDER))


def load(judge_csv, rounds_csv):
    j = pd.read_csv(judge_csv)
    j["model"] = j["target_model_version"].map(pretty)
    # join breach flag from rounds.csv on (run_id, round_index)
    r = pd.read_csv(rounds_csv, low_memory=False)[["run_id", "round_index", "breach_this_round"]]
    j = j.merge(r, on=["run_id", "round_index"], how="left")
    return j


def fig_verdict_by_model(j, out):
    style()
    models = order_models(j["model"].unique())
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    bottoms = np.zeros(len(models))
    for v in VERDICTS:
        fracs = []
        for m in models:
            sub = j[j["model"] == m]
            fracs.append((sub["verdict"] == v).mean() if len(sub) else 0.0)
        fracs = np.array(fracs)
        ax.bar(range(len(models)), fracs, bottom=bottoms, color=VCOLOR[v], label=VLABEL[v], width=0.6)
        for i, (f, b) in enumerate(zip(fracs, bottoms)):
            if f > 0.04:
                ax.text(i, b + f / 2, f"{f*100:.0f}%", ha="center", va="center",
                        color="white", fontweight="bold", fontsize=10)
        bottoms += fracs
    ns = [int((j["model"] == m).sum()) for m in models]
    ax.set_xticks(range(len(models)), [f"{m}\n(n={n})" for m, n in zip(models, ns)])
    ax.set_ylim(0, 1.0); ax.set_ylabel("share of judged replies")
    ax.set_title("Judge verdicts by model (SECONDARY, advisory)", fontweight="bold", pad=34)
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.16), fontsize=9)
    fig.tight_layout(); fig.savefig(out, bbox_inches="tight"); plt.close(fig)


def fig_degradation_by_round(j, out, k_max=10):
    style()
    models = order_models(j["model"].unique())
    fig, ax = plt.subplots(figsize=(7.8, 4.6))
    for m in models:
        sub = j[j["model"] == m]
        xs, ys = [], []
        for k in range(1, k_max + 1):
            g = sub[sub["round_index"] == k]
            if len(g) >= 3:
                xs.append(k); ys.append(g["normalized_score"].mean())
        if xs:
            ax.plot(xs, ys, "-o", color=MCOLOR.get(m, "#555"), lw=2.2, ms=5, label=m)
    ax.set_xlim(0.5, k_max + 0.5); ax.set_ylim(-0.02, 1.02); ax.set_xticks(range(1, k_max + 1))
    ax.set_xlabel("attack round k"); ax.set_ylabel("mean degradation (0–1)")
    ax.set_title("Does the persona erode over rounds? (Judge degradation vs round)", fontweight="bold")
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    fig.tight_layout(); fig.savefig(out, bbox_inches="tight"); plt.close(fig)


def fig_degradation_breach_vs_hold(j, out):
    style()
    jb = j.dropna(subset=["breach_this_round"])
    if jb.empty:
        return
    groups = [("non-breach round", jb[jb["breach_this_round"] == 0]),
              ("breach round", jb[jb["breach_this_round"] == 1])]
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    labels, means, sems, colors = [], [], [], []
    for name, g in groups:
        if len(g):
            labels.append(f"{name}\n(n={len(g)})"); means.append(g["normalized_score"].mean())
            sems.append(g["normalized_score"].std() / max(1, np.sqrt(len(g))))
            colors.append("#0072B2" if "non" in name else "#D55E00")
    ax.bar(range(len(labels)), means, yerr=sems, width=0.55, color=colors, capsize=6,
           error_kw=dict(ecolor=MUTED, lw=1.2))
    for i, mv in enumerate(means):
        ax.text(i, mv + 0.02, f"{mv:.2f}", ha="center", va="bottom", fontweight="bold")
    ax.set_xticks(range(len(labels)), labels); ax.set_ylim(0, 1.05)
    ax.set_ylabel("mean Judge degradation (0–1)")
    ax.set_title("Concordance check: degradation on breach vs non-breach rounds", fontweight="bold")
    ax.text(0.5, -0.2, "Deterministic breaches coincide with high qualitative degradation — but the "
            "Judge NEVER defines a breach.", transform=ax.transAxes, ha="center", fontsize=8, color=MUTED)
    fig.tight_layout(); fig.savefig(out, bbox_inches="tight"); plt.close(fig)


def fig_verdict_by_scenario(j, out):
    style()
    scens = [s for s in ["conf_vault_v1", "integ_override_v1"] if s in set(j["scenario_id"])]
    slabel = {"conf_vault_v1": "Confidentiality", "integ_override_v1": "Integrity"}
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    bottoms = np.zeros(len(scens))
    for v in VERDICTS:
        fracs = np.array([(j[j["scenario_id"] == s]["verdict"] == v).mean() for s in scens])
        ax.bar(range(len(scens)), fracs, bottom=bottoms, color=VCOLOR[v], label=VLABEL[v], width=0.55)
        for i, (f, b) in enumerate(zip(fracs, bottoms)):
            if f > 0.04:
                ax.text(i, b + f / 2, f"{f*100:.0f}%", ha="center", va="center", color="white", fontweight="bold")
        bottoms += fracs
    ax.set_xticks(range(len(scens)), [slabel[s] for s in scens]); ax.set_ylim(0, 1.0)
    ax.set_ylabel("share of judged replies")
    ax.set_title("Judge verdicts by boundary type", fontweight="bold", pad=34)
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.16), fontsize=9)
    fig.tight_layout(); fig.savefig(out, bbox_inches="tight"); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge-csv", default=str(ROOT / "output" / "judge_scores.csv"))
    ap.add_argument("--rounds-csv", default=str(ROOT / "output" / "rounds_3models.csv"))
    ap.add_argument("--out", default=str(ROOT / "output" / "figures"))
    args = ap.parse_args()
    jp = Path(args.judge_csv)
    if not jp.exists():
        print(f"no judge scores yet at {jp} — skipping judge figures")
        return
    j = load(jp, Path(args.rounds_csv))
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    cov = j.groupby("target_model_version")["verdict"].count().to_dict()
    print(f"judge coverage: {len(j)} judged rounds | per model: { {pretty(k): v for k,v in cov.items()} }")
    fig_verdict_by_model(j, out / "fig_judge_verdict_by_model.png")
    fig_degradation_by_round(j, out / "fig_judge_degradation_by_round.png")
    fig_degradation_breach_vs_hold(j, out / "fig_judge_breach_concordance.png")
    fig_verdict_by_scenario(j, out / "fig_judge_verdict_by_scenario.png")
    print("judge figures written")


if __name__ == "__main__":
    main()
