#!/usr/bin/env python3
"""Presentation figure gallery (Plotly) — the slide-ready charts in results/figures/.

Rebuilds ALL BreachBenchmark figures under ONE design system: a fixed per-model color used in
every panel, cleaned labels, value labels lifted clear of the error bars. Exports high-res
static PNGs via kaleido. Runs entirely offline off the committed dataset.

    python scripts/make_figures.py                    # the whole gallery
    python scripts/make_figures.py --rounds-csv ...   # against a different dataset

Primary (deterministic) figures always render; the secondary Judge figures render only if the
judge scores CSV exists, and print their coverage so a partial pass is never mistaken for a
census. An earlier matplotlib gallery was replaced by this one — see FIGURES.md.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from breachbench.analysis.km import kaplan_meier  # noqa: E402
from breachbench.analysis.labels import prettify_model  # noqa: E402
from breachbench.analysis.loader import load_cell_observations  # noqa: E402

# ---------- design system ----------
# Ordered weakest -> strongest, mirroring the roster in config/experiment.yaml. Colors are
# assigned per MODEL and never cycled per-panel: one model wears one color in every figure.
MODEL_ORDER = ["gpt-3.5-turbo", "gpt-5-nano", "gpt-4o-mini"]
MC = {"gpt-3.5-turbo": "#D55E00", "gpt-5-nano": "#E69F00", "gpt-4o-mini": "#009E73"}
MYEAR = {"gpt-3.5-turbo": 2023, "gpt-4o-mini": 2024, "gpt-5-nano": 2025}
MNOTE = {"gpt-3.5-turbo": "2023 · older", "gpt-4o-mini": "2024 · efficient", "gpt-5-nano": "2025 · newest, tiny"}
VEC_ORDER = ["ROLEPLAY", "AUTHORITY", "CIPHER", "MANY_SHOT"]
SCEN = {"conf_vault_v1": "Confidentiality", "integ_override_v1": "Integrity"}
VERDICTS = ["NO_DEGRADATION", "WEAK_REFUSAL", "PERSONA_BREAK"]
VC = {"NO_DEGRADATION": "#009E73", "WEAK_REFUSAL": "#E69F00", "PERSONA_BREAK": "#D55E00"}
VLAB = {"NO_DEGRADATION": "No degradation", "WEAK_REFUSAL": "Weak refusal", "PERSONA_BREAK": "Persona break"}

INK, MUTED, GRID = "#1f2733", "#6b7280", "#eef1f5"
FONT = "Arial, Helvetica, sans-serif"

LAYOUT = dict(
    template="plotly_white", font=dict(family=FONT, size=16, color=INK),
    title=dict(font=dict(size=22, color=INK), x=0.5, xanchor="center", y=0.96),
    paper_bgcolor="white", plot_bgcolor="white",
    margin=dict(l=80, r=40, t=90, b=70),
)
AXIS = dict(showgrid=True, gridcolor=GRID, zeroline=False, linecolor=MUTED,
            ticks="outside", tickcolor=MUTED, title_font=dict(size=16), tickfont=dict(size=14))


pretty = prettify_model  # single-sourced from breachbench.analysis.labels


def order_models(ms):
    ms = set(ms)
    return [m for m in MODEL_ORDER if m in ms] + sorted(ms - set(MODEL_ORDER))


def save(fig, out, w, h):
    fig.write_image(str(out), width=w, height=h, scale=2)
    print(f"  wrote {Path(out).name}")


def labels_above_errorbars(fig, xs, ys, errs_hi, texts, pad, size=20):
    """Place value labels clear ABOVE each error-bar cap (avoids whisker collision)."""
    for x, y, e, t in zip(xs, ys, errs_hi, texts):
        fig.add_annotation(x=x, y=y + e + pad, text=t, showarrow=False,
                           font=dict(size=size, color=INK), yanchor="bottom")


# ---------- data ----------
def build(rounds_csv):
    cells = load_cell_observations(rounds_csv)
    return [dict(model=pretty(c.target_model_version), scenario=c.scenario_id,
                 vector=c.attack_vector, durations=c.durations, events=c.events) for c in cells]


def pool(rows, model=None, scenario=None, vector=None):
    du, ev = [], []
    for r in rows:
        if model and r["model"] != model:
            continue
        if scenario and r["scenario"] != scenario:
            continue
        if vector and r["vector"] != vector:
            continue
        du.append(r["durations"]); ev.append(r["events"])
    if not ev:
        return np.array([]), np.array([])
    return np.concatenate(du), np.concatenate(ev)


def boot(ev, B=5000, seed=7):
    if len(ev) == 0:
        return 0.0, 0.0, 0.0
    est = float(ev.mean())
    if len(ev) == 1:
        return est, est, est
    rng = np.random.default_rng(seed)
    s = ev[rng.integers(0, len(ev), size=(B, len(ev)))].mean(axis=1)
    return est, float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))


# ============================================================ PRIMARY
def f_asr_by_model(rows, out):
    models = order_models({r["model"] for r in rows})
    est, elo, ehi, ns = [], [], [], []
    for m in models:
        _, ev = pool(rows, model=m); e, l, h = boot(ev)
        est.append(e); elo.append(e - l); ehi.append(h - e); ns.append(len(ev))
    xlab = [f"{m}<br><span style='font-size:13px;color:{MUTED}'>{MNOTE[m]}</span>" for m in models]
    fig = go.Figure(go.Bar(
        x=xlab, y=est, marker_color=[MC[m] for m in models], width=0.6,
        error_y=dict(type="data", symmetric=False, array=ehi, arrayminus=elo, color=MUTED, thickness=1.6, width=8),
    ))
    labels_above_errorbars(fig, xlab, est, ehi, [f"<b>{e*100:.0f}%</b>" for e in est], pad=0.03, size=22)
    fig.update_layout(**LAYOUT, showlegend=False,
                      title_text="How breakable is each model?  Overall attack success rate")
    fig.update_yaxes(range=[0, 1.08], tickformat=".0%", title_text="ASR @ 10 rounds", **AXIS)
    fig.update_xaxes(**AXIS)
    fig.add_annotation(x=0.5, xref="paper", y=-0.16, yref="paper", showarrow=False,
                       text=f"Pooled over 2 boundaries × 4 attack vectors × 20 reps (n≈{ns[0]} runs/model). "
                            f"Whiskers = bootstrap 95% CI.", font=dict(size=12, color=MUTED))
    save(fig, out, 900, 560)


def f_km_by_model(rows, out, k_max=10):
    models = order_models({r["model"] for r in rows})
    fig = go.Figure()
    for m in models:
        du, ev = pool(rows, model=m); km = kaplan_meier(du, ev, k_max)
        x = np.concatenate([[0], km.k]); s = np.concatenate([[1.0], km.survival])
        fig.add_trace(go.Scatter(x=x, y=s, mode="lines", line=dict(color=MC[m], width=3.5, shape="hv"),
                                 name=f"{m}  (n={len(ev)})"))
    fig.update_layout(**LAYOUT, legend=dict(x=0.98, y=0.98, xanchor="right", yanchor="top",
                      bgcolor="rgba(255,255,255,0.7)", font=dict(size=15)),
                      title_text="Survival under sustained attack (pooled over all vectors)")
    fig.update_yaxes(range=[-0.03, 1.03], tickformat=".0%",
                     title_text="Ŝ(k) — probability the boundary still holds", **AXIS)
    fig.update_xaxes(range=[0, k_max], dtick=1, title_text="attack round k", **AXIS)
    save(fig, out, 900, 560)


def f_km_facet(rows, scenario, out, k_max=10):
    models = order_models({r["model"] for r in rows if r["scenario"] == scenario})
    vectors = [v for v in VEC_ORDER if any(r["vector"] == v and r["scenario"] == scenario for r in rows)]
    fig = make_subplots(rows=2, cols=2, subplot_titles=vectors, horizontal_spacing=0.10, vertical_spacing=0.16)
    for i, vec in enumerate(vectors):
        rr, cc = i // 2 + 1, i % 2 + 1
        for m in models:
            du, ev = pool(rows, model=m, scenario=scenario, vector=vec)
            if not len(ev):
                continue
            km = kaplan_meier(du, ev, k_max)
            x = np.concatenate([[0], km.k]); s = np.concatenate([[1.0], km.survival])
            fig.add_trace(go.Scatter(x=x, y=s, mode="lines", line=dict(color=MC[m], width=3, shape="hv"),
                                     name=m, legendgroup=m, showlegend=(i == 0)), row=rr, col=cc)
        fig.update_yaxes(range=[-0.03, 1.03], tickformat=".0%", gridcolor=GRID, row=rr, col=cc)
        fig.update_xaxes(range=[0, k_max], dtick=2, gridcolor=GRID, row=rr, col=cc)
    fig.update_layout(**{k: v for k, v in LAYOUT.items() if k != "margin"},
                      margin=dict(l=70, r=40, t=130, b=60),
                      legend=dict(orientation="h", x=0.5, xanchor="center", y=1.11, yanchor="bottom", font=dict(size=14)),
                      title_text=f"Kaplan–Meier survival by attack vector — {SCEN.get(scenario, scenario)}")
    fig.update_annotations(font_size=15)
    save(fig, out, 1000, 740)


def f_grouped_asr(rows, cats, cat_key, title, out, catlabels=None):
    models = order_models({r["model"] for r in rows})
    fig = go.Figure()
    for m in models:
        ys = []
        for c in cats:
            kw = {cat_key: c}
            _, ev = pool(rows, model=m, **kw)
            ys.append(ev.mean() if len(ev) else 0.0)
        fig.add_trace(go.Bar(name=m, x=catlabels or cats, y=ys, marker_color=MC[m],
                             text=[f"{v:.2f}" for v in ys], textposition="outside",
                             textfont=dict(size=13, color=INK), cliponaxis=False))
    fig.update_layout(**LAYOUT, barmode="group", bargap=0.28, bargroupgap=0.08,
                      legend=dict(orientation="h", x=0.5, xanchor="center", y=1.10, font=dict(size=15)),
                      title_text=title)
    fig.update_yaxes(range=[0, 1.12], tickformat=".0%", title_text="ASR @ 10 rounds", **AXIS)
    fig.update_xaxes(**AXIS)
    save(fig, out, 950, 560)


def f_breach_hist(rows, out, k_max=10):
    models = order_models({r["model"] for r in rows})
    fig = make_subplots(rows=1, cols=len(models),
                        subplot_titles=[f"{m}<br><span style='font-size:12px;color:{MUTED}'>"
                                        f"{int((pool(rows,model=m)[1]==1).sum())} breaches / "
                                        f"{len(pool(rows,model=m)[1])} runs</span>" for m in models])
    ymax = 0
    for j, m in enumerate(models, 1):
        du, ev = pool(rows, model=m); br = du[ev == 1]
        counts, _ = np.histogram(br, bins=np.arange(0.5, k_max + 1.5))
        ymax = max(ymax, counts.max() if len(counts) else 0)
        fig.add_trace(go.Bar(x=list(range(1, k_max + 1)), y=counts, marker_color=MC[m],
                             marker_line=dict(color="white", width=1), showlegend=False), row=1, col=j)
        fig.update_xaxes(title_text="breach round k", dtick=1, gridcolor=GRID, row=1, col=j)
        fig.update_yaxes(gridcolor=GRID, row=1, col=j)
    for j in range(1, len(models) + 1):
        fig.update_yaxes(range=[0, ymax * 1.12], row=1, col=j)
    fig.update_yaxes(title_text="number of breaches", row=1, col=1)
    fig.update_layout(**{k: v for k, v in LAYOUT.items() if k != "margin"},
                      margin=dict(l=70, r=30, t=110, b=70), showlegend=False,
                      title_text="When do breaches happen? Distribution of breach round")
    fig.update_annotations(font_size=15)
    save(fig, out, 1150, 470)


def f_heatmap(rows, out):
    models = order_models({r["model"] for r in rows})
    scens = [s for s in ["conf_vault_v1", "integ_override_v1"] if any(r["scenario"] == s for r in rows)]
    vectors = [v for v in VEC_ORDER if any(r["vector"] == v for r in rows)][::-1]  # top-down nice order
    fig = make_subplots(rows=1, cols=len(scens), subplot_titles=[SCEN[s] for s in scens],
                        horizontal_spacing=0.13)
    for ci, sc in enumerate(scens, 1):
        z = [[pool(rows, model=m, scenario=sc, vector=v)[1].mean()
              if len(pool(rows, model=m, scenario=sc, vector=v)[1]) else np.nan
              for m in models] for v in vectors]
        txt = [[f"<b>{val:.2f}</b>" if not np.isnan(val) else "" for val in row] for row in z]
        fig.add_trace(go.Heatmap(z=z, x=models, y=vectors, text=txt, texttemplate="%{text}",
                                 textfont=dict(size=15), colorscale="Reds", zmin=0, zmax=1,
                                 showscale=(ci == len(scens)), xgap=3, ygap=3,
                                 colorbar=dict(title="ASR", len=0.9, thickness=16)), row=1, col=ci)
        fig.update_xaxes(tickangle=-15, row=1, col=ci)
    fig.update_layout(**{k: v for k, v in LAYOUT.items() if k != "margin"},
                      margin=dict(l=90, r=40, t=100, b=70),
                      title_text="Attack success rate — model × attack vector")
    fig.update_annotations(font_size=16)
    save(fig, out, 1050, 520)


def f_capability(rows, out):
    models = order_models({r["model"] for r in rows})
    fig = go.Figure()
    for m in models:
        _, ev = pool(rows, model=m); rob = 1 - ev.mean()
        fig.add_trace(go.Scatter(x=[MYEAR[m]], y=[rob], mode="markers+text",
                                 marker=dict(size=34, color=MC[m], line=dict(color="white", width=2)),
                                 text=[f"<b>{m}</b><br>{rob*100:.0f}% held"], textposition="top center",
                                 textfont=dict(size=14), showlegend=False))
    fig.update_layout(**LAYOUT, title_text="Newer ≠ safer: capability, not recency, drives robustness")
    fig.update_yaxes(range=[-0.05, 1.15], tickformat=".0%", title_text="overall robustness (1 − ASR)", **AXIS)
    fig.update_xaxes(range=[2022.5, 2025.5], dtick=1, title_text="model release year", **AXIS)
    fig.add_annotation(x=0.5, xref="paper", y=-0.17, yref="paper", showarrow=False,
                       text="The 2025 tiny model (gpt-5-nano) is MORE breakable than the 2024 gpt-4o-mini.",
                       font=dict(size=12, color=MUTED))
    save(fig, out, 900, 560)


# ============================================================ SECONDARY (judge)
def load_judge(judge_csv, rounds_csv):
    j = pd.read_csv(judge_csv); j["model"] = j["target_model_version"].map(pretty)
    r = pd.read_csv(rounds_csv, low_memory=False)[["run_id", "round_index", "breach_this_round"]]
    return j.merge(r, on=["run_id", "round_index"], how="left")


def f_judge_verdict(j, group_key, cats, catlabels, title, out):
    fig = go.Figure()
    for v in VERDICTS:
        fracs, texts = [], []
        for c in cats:
            sub = j[j[group_key] == c]
            f = (sub["verdict"] == v).mean() if len(sub) else 0.0
            fracs.append(f); texts.append(f"{f*100:.0f}%" if f > 0.04 else "")
        fig.add_trace(go.Bar(name=VLAB[v], x=catlabels, y=fracs, marker_color=VC[v],
                             text=texts, textposition="inside", insidetextanchor="middle",
                             textfont=dict(size=15, color="white")))
    fig.update_layout(**LAYOUT, barmode="stack", bargap=0.4,
                      legend=dict(orientation="h", x=0.5, xanchor="center", y=1.10, font=dict(size=14)),
                      title_text=title)
    fig.update_yaxes(range=[0, 1.0], tickformat=".0%", title_text="share of judged replies", **AXIS)
    fig.update_xaxes(**AXIS)
    save(fig, out, 850, 560)


def f_judge_degradation_by_model(j, out):
    models = order_models(j["model"].unique())
    means, sems, ns = [], [], []
    for m in models:
        g = j[j["model"] == m]["normalized_score"]
        means.append(g.mean()); sems.append(g.std() / max(1, np.sqrt(len(g)))); ns.append(len(g))
    xlab = [f"{m}<br><span style='font-size:12px;color:{MUTED}'>(n={n})</span>" for m, n in zip(models, ns)]
    fig = go.Figure(go.Bar(
        x=xlab, y=means, marker_color=[MC[m] for m in models], width=0.6,
        error_y=dict(type="data", array=sems, color=MUTED, thickness=1.6, width=8)))
    labels_above_errorbars(fig, xlab, means, sems, [f"<b>{v:.2f}</b>" for v in means], pad=0.02, size=18)
    fig.update_layout(**LAYOUT, showlegend=False,
                      title_text="Judge-rated degradation by model (0 = in persona, 1 = collapsed)")
    fig.update_yaxes(range=[0, max(means) * 1.35 + 0.08], title_text="mean degradation (0–1)", **AXIS)
    fig.update_xaxes(**AXIS)
    save(fig, out, 850, 540)


def f_judge_concordance(j, out):
    jb = j.dropna(subset=["breach_this_round"])
    if jb.empty:
        return
    groups = [("non-breach round", jb[jb["breach_this_round"] == 0], "#0072B2"),
              ("breach round", jb[jb["breach_this_round"] == 1], "#D55E00")]
    xs, ys, es, cs = [], [], [], []
    for name, g, col in groups:
        if len(g):
            xs.append(f"{name}<br><span style='font-size:12px;color:{MUTED}'>(n={len(g)})</span>")
            ys.append(g["normalized_score"].mean()); es.append(g["normalized_score"].std() / max(1, np.sqrt(len(g)))); cs.append(col)
    fig = go.Figure(go.Bar(x=xs, y=ys, marker_color=cs, width=0.5,
                           error_y=dict(type="data", array=es, color=MUTED, thickness=1.6, width=8)))
    labels_above_errorbars(fig, xs, ys, es, [f"<b>{v:.2f}</b>" for v in ys], pad=0.03, size=18)
    fig.update_layout(**LAYOUT, showlegend=False,
                      title_text="Concordance: degradation on breach vs non-breach rounds")
    fig.update_yaxes(range=[0, min(1.05, max(ys) + max(es) + 0.16)], title_text="mean Judge degradation (0–1)", **AXIS)
    fig.update_xaxes(**AXIS)
    fig.add_annotation(x=0.5, xref="paper", y=-0.16, yref="paper", showarrow=False,
                       text="The Judge independently rates breach rounds as far more degraded — but it never DEFINES a breach.",
                       font=dict(size=12, color=MUTED))
    save(fig, out, 820, 540)


def f_judge_vs_deterministic(j, out):
    """What the Judge ADDS over the deterministic detector: on rounds where the detector
    fired, the Judge strongly agrees; but the Judge also flags 'soft' degradation on many
    rounds with NO breach — erosion the code-based detector cannot see."""
    jb = j.dropna(subset=["breach_this_round"]).copy()
    if jb.empty:
        return
    jb["degraded"] = jb["verdict"].isin(["PERSONA_BREAK", "WEAK_REFUSAL"])
    groups = [("Deterministic BREACH", jb[jb["breach_this_round"] == 1]),
              ("No breach (detector)", jb[jb["breach_this_round"] == 0])]
    fig = go.Figure()
    cats = [f"{name}<br><span style='font-size:12px;color:{MUTED}'>(n={len(g)})</span>" for name, g in groups]
    deg = [g["degraded"].mean() for _, g in groups]
    intact = [1 - d for d in deg]
    fig.add_trace(go.Bar(name="Judge: persona degraded", x=cats, y=deg, marker_color="#D55E00",
                         text=[f"{d*100:.0f}%" for d in deg], textposition="inside",
                         insidetextanchor="middle", textfont=dict(size=16, color="white")))
    fig.add_trace(go.Bar(name="Judge: persona intact", x=cats, y=intact, marker_color="#009E73",
                         text=[f"{v*100:.0f}%" if v > 0.05 else "" for v in intact], textposition="inside",
                         insidetextanchor="middle", textfont=dict(size=16, color="white")))
    fig.update_layout(**LAYOUT, barmode="stack", bargap=0.45,
                      legend=dict(orientation="h", x=0.5, xanchor="center", y=1.10, font=dict(size=14)),
                      title_text="What the Judge adds: qualitative degradation vs actual breaches")
    fig.update_yaxes(range=[0, 1.0], tickformat=".0%", title_text="share of rounds", **AXIS)
    fig.update_xaxes(**AXIS)
    fig.add_annotation(x=0.5, xref="paper", y=-0.17, yref="paper", showarrow=False,
                       text="On rounds the detector flags, the Judge agrees ~94%. The Judge ALSO flags 'soft' degradation on "
                            "many no-breach rounds — erosion the code detector can't see.", font=dict(size=11.5, color=MUTED))
    save(fig, out, 900, 560)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds-csv", default=str(ROOT / "data" / "rounds_benchmark.csv"))
    ap.add_argument("--judge-csv", default=str(ROOT / "data" / "judge_scores.csv"))
    ap.add_argument("--out", default=str(ROOT / "results" / "figures"))
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    rows = build(Path(args.rounds_csv))
    print(f"loaded {len(rows)} cells; models: {order_models({r['model'] for r in rows})}")
    # remove redundant old-style copies
    for old in ["fig_asr_heatmap_conf.png", "fig_asr_heatmap_integ.png",
                "fig_km_smallmultiples_conf.png", "fig_km_smallmultiples_integ.png",
                "fig_judge_degradation_by_round.png"]:
        (out / old).unlink(missing_ok=True)

    f_asr_by_model(rows, out / "fig_asr_by_model.png")
    f_km_by_model(rows, out / "fig_km_by_model.png")
    f_km_facet(rows, "conf_vault_v1", out / "fig_km_facet_conf.png")
    f_km_facet(rows, "integ_override_v1", out / "fig_km_facet_integ.png")
    f_grouped_asr(rows, VEC_ORDER, "vector", "Which attack strategy works best? (ASR by vector)",
                  out / "fig_asr_by_vector.png")
    f_grouped_asr(rows, ["conf_vault_v1", "integ_override_v1"], "scenario",
                  "Confidentiality vs Integrity — ASR by boundary", out / "fig_asr_by_scenario.png",
                  catlabels=["Confidentiality (canary)", "Integrity (tool)"])
    f_breach_hist(rows, out / "fig_breach_round_hist.png")
    f_heatmap(rows, out / "fig_heatmap_model_vector.png")
    f_capability(rows, out / "fig_capability_vs_recency.png")
    print("primary figures done")

    jp = Path(args.judge_csv)
    if jp.exists():
        j = load_judge(jp, Path(args.rounds_csv))
        models = order_models(j["model"].unique())
        print(f"judge coverage: {len(j)} rounds")
        f_judge_verdict(j, "model", models,
                        [f"{m}<br><span style='font-size:12px;color:{MUTED}'>(n={int((j['model']==m).sum())})</span>" for m in models],
                        "Judge verdicts by model (secondary, advisory)", out / "fig_judge_verdict_by_model.png")
        scens = [s for s in ["conf_vault_v1", "integ_override_v1"] if s in set(j["scenario_id"])]
        f_judge_verdict(j, "scenario_id", scens, [SCEN[s] for s in scens],
                        "Judge verdicts by boundary type", out / "fig_judge_verdict_by_scenario.png")
        f_judge_degradation_by_model(j, out / "fig_judge_degradation_by_model.png")
        f_judge_concordance(j, out / "fig_judge_breach_concordance.png")
        f_judge_vs_deterministic(j, out / "fig_judge_vs_deterministic.png")
        print("judge figures done")
    else:
        print("no judge_scores.csv — skipped judge figures")


if __name__ == "__main__":
    main()
