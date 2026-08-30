"""Analysis entry point: rounds.csv -> KM curves, ASR@k_max table + heatmaps, and
pre-registered log-rank tests. Writes CSV artifacts and returns a text summary.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from ..config.schema import ExperimentConfig
from .asr import asr_heatmap_matrix, asr_table
from .km import kaplan_meier
from .labels import prettify_model
from .loader import CellObservations, load_cell_observations, load_summary_frame
from .logrank import logrank_test


def _run_census(rounds_csv: str | Path) -> dict[str, int]:
    """Operational census of the runs behind the analysis.

    Administrative censoring (a non-transient failure after at least one valid round) is a
    *real* censoring event but not a *model* outcome, so its count is reported explicitly
    rather than left buried — a reader can then decide whether to exclude it. Transient
    failures never reach here: they invalidate + reschedule (see docs/PREREGISTRATION.md §3B).
    """
    try:
        df = load_summary_frame(rounds_csv)
    except Exception:  # a census is nice-to-have; never fail the analysis over it
        return {}
    valid = df[df["run_valid"] == 1]
    reasons = valid["termination_reason"].astype(str).value_counts()
    return {
        "admin_censored": int(reasons.get("ADMIN_CENSORED_ERROR", 0)),
        "budget_exhausted": int(reasons.get("BUDGET_EXHAUSTED", 0)),
        "invalid": int((df["run_valid"] != 1).sum()),
    }


def _survival_curves_frame(cells: list[CellObservations], k_max: int) -> pd.DataFrame:
    rows = []
    for c in cells:
        km = kaplan_meier(c.durations, c.events, k_max)
        for i, k in enumerate(km.k):
            rows.append({
                "cell_id": c.cell_id,
                "target_model_version": c.target_model_version,
                "scenario_id": c.scenario_id,
                "attack_vector": c.attack_vector,
                "k": int(k),
                "survival": km.survival[i],
                "asr": km.asr[i],
                "ci_lower": km.ci_lower[i],
                "ci_upper": km.ci_upper[i],
                "n_at_risk": int(km.n_at_risk[i]),
                "n_events": int(km.n_events[i]),
            })
    return pd.DataFrame(rows)


def _round_sig(x: float, figs: int = 8) -> float:
    """Round to `figs` significant figures.

    chi2 is a pure-Python running sum (platform-independent), but its p-value goes through
    scipy's chi2 survival function — and pyproject.toml pins no scipy upper bound, so CI
    installs whatever is newest at build time. A scipy patch release can shift that special
    function's last 1-2 digits, which turns into a spurious byte-diff on logrank.csv against
    the committed file even though the result is scientifically identical. 8 significant
    figures is far more precision than a p-value or chi2 statistic needs (the report only ever
    displays 4), and comfortably absorbs that noise without rounding away anything meaningful.
    """
    if x == 0 or not math.isfinite(x):
        return x
    from math import floor, log10

    return round(x, figs - int(floor(log10(abs(x)))) - 1)


def _run_logrank_pairs(
    cells: list[CellObservations], config: ExperimentConfig
) -> pd.DataFrame:
    from ..loop.types import Cell

    # Match on the STABLE configured cell identity (cell_id), not the resolved
    # model-version string — the latter drifts (e.g. "gpt-4o" -> "gpt-4o-2024-08-06")
    # and would never match a pre-registered pair declared with configured names.
    lookup = {c.cell_id: c for c in cells}
    rows = []
    for pair in config.logrank_pairs:
        cell_a = Cell(target=pair.model_a, scenario_id=pair.scenario_id,
                      attack_vector=pair.attack_vector).cell_id()
        cell_b = Cell(target=pair.model_b, scenario_id=pair.scenario_id,
                      attack_vector=pair.attack_vector).cell_id()
        a, b = lookup.get(cell_a), lookup.get(cell_b)
        if a is None or b is None:
            # A pre-registered pair naming a model this dataset doesn't contain. Emit blanks,
            # not NaN: the row is "we declared this and could not compute it", which reads as
            # a deliberate statement rather than a broken table. See docs/PREREGISTRATION.md.
            rows.append({
                "scenario_id": pair.scenario_id,
                "attack_vector": pair.attack_vector.value,
                "model_a": pair.model_a.model_version,
                "model_b": pair.model_b.model_version,
                "status": "NOT_COLLECTED",
                "chi2": "",
                "p_value": "",
                "n_a": "",
                "n_b": "",
                "underpowered": "",
            })
            continue
        res = logrank_test(a.durations, a.events, b.durations, b.events, config.k_max)
        rows.append({
            "scenario_id": pair.scenario_id,
            "attack_vector": pair.attack_vector.value,
            "model_a": pair.model_a.model_version,
            "model_b": pair.model_b.model_version,
            "status": "OK",
            "chi2": _round_sig(res.chi2),
            "p_value": _round_sig(res.p_value),
            "n_a": res.n_a,
            "n_b": res.n_b,
            "underpowered": res.underpowered,
        })
    return pd.DataFrame(rows)


def analyze_and_report(
    rounds_csv: str | Path,
    out_dir: str | Path,
    *,
    config: ExperimentConfig,
    bootstrap_B: int = 2000,
) -> str:
    """Run the full analysis and write artifacts. `bootstrap_B` defaults to 2000 for
    responsiveness; set to 10000 for final reporting (Appendix B)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cells = load_cell_observations(rounds_csv)

    curves = _survival_curves_frame(cells, config.k_max)
    curves.to_csv(out_dir / "survival_curves.csv", index=False)

    table = asr_table(cells, config.k_max, bootstrap_B=bootstrap_B)
    table.to_csv(out_dir / "asr_table.csv", index=False)

    for scenario_id in sorted({c.scenario_id for c in cells}):
        heat = asr_heatmap_matrix(table, scenario_id)
        heat.to_csv(out_dir / f"asr_heatmap_{scenario_id}.csv")

    logrank_df = _run_logrank_pairs(cells, config)
    if not logrank_df.empty:
        logrank_df.to_csv(out_dir / "logrank.csv", index=False)

    # Figures (KM curves + ASR heatmaps) + a human-readable markdown report.
    figures: list = []
    try:
        from .plots import generate_figures, summary_table_markdown

        figures = generate_figures(cells, table, config.k_max, out_dir, bootstrap_B=bootstrap_B)
        _write_markdown_report(out_dir, cells, table, logrank_df, figures,
                               summary_table_markdown(table), config,
                               census=_run_census(rounds_csv))
    except Exception as exc:  # matplotlib missing or a plotting error must not lose the CSVs
        (out_dir / "PLOTS_SKIPPED.txt").write_text(f"figure generation skipped: {exc}\n")

    n_cells = len(cells)
    total_runs = int(sum(c.n for c in cells))
    total_events = int(sum(c.n_events for c in cells))
    total_censored = int(sum(c.n_censored for c in cells))
    mean_asr = float(table["asr_at_kmax"].mean()) if not table.empty else float("nan")

    lines = [
        f"Analyzed {n_cells} cells, {total_runs} valid runs "
        f"({total_events} breaches, {total_censored} censored).",
        f"Mean ASR@k_max across cells: {mean_asr:.3f}",
        f"Artifacts written to: {out_dir}",
        "  - survival_curves.csv (Ŝ(k) + cloglog CI per cell)",
        f"  - asr_table.csv (ASR@k_max + bootstrap CI, B={bootstrap_B})",
        "  - asr_heatmap_<scenario>.csv (vectors × models)",
    ]
    if not logrank_df.empty:
        lines.append(f"  - logrank.csv ({len(logrank_df)} pre-registered pair(s))")
    else:
        lines.append("  - logrank.csv omitted (no pre-registered pairs; locked list is empty)")
    if figures:
        lines.append(f"  - {len(figures)} figure(s): km_<scenario>.png, asr_heatmap_<scenario>.png")
        lines.append("  - REPORT.md (human-readable summary with tables + figure links)")
    return "\n".join(lines)


def _write_markdown_report(out_dir, cells, table, logrank_df, figures, summary_md, config,
                           census: dict[str, int] | None = None) -> None:
    n_cells = len(cells)
    total_runs = int(sum(c.n for c in cells))
    total_events = int(sum(c.n_events for c in cells))
    total_censored = int(sum(c.n_censored for c in cells))
    scenarios = sorted({c.scenario_id for c in cells})
    models = sorted({prettify_model(c.target_model_version) for c in cells})
    census = census or {}

    admin = census.get("admin_censored")
    if admin is None:
        admin_line = ""
    elif admin == 0:
        admin_line = (
            "- **Administrative censoring:** 0 runs. Every censored run above is a genuine "
            f"survival to k_max = {config.k_max}, not an operational failure. (Transient "
            "failures invalidate + reschedule rather than censor — see "
            "[pre-registration §3B](../../docs/PREREGISTRATION.md).)"
        )
    else:
        admin_line = (
            f"- **Administrative censoring:** {admin} run(s) ended in `ADMIN_CENSORED_ERROR` "
            "(a non-transient operational failure after ≥1 valid round). They are censored, "
            "not breached; exclude them for a model-only view."
        )

    md = [
        "# BreachBenchmark — Results",
        "",
        f"- **Cells analyzed:** {n_cells}  ·  **valid runs:** {total_runs}  "
        f"(**{total_events}** breaches, **{total_censored}** censored)",
        f"- **Targets:** {', '.join(models)}  ·  **Attacker (fixed instrument):** "
        f"`{config.attacker.vendor.value}:{config.attacker.model_version}`",
        f"- **k_max:** {config.k_max}  ·  **repetitions target (N):** {config.repetitions}  "
        f"·  Judge: {'on' if config.judge.enabled else 'off (primary metrics are deterministic)'}",
        "- ASR@k_max is derived from the Kaplan–Meier curve (1 − Ŝ(k_max)), so right-censoring "
        "is handled correctly; CIs are bootstrap (resampling runs within each cell).",
        *([admin_line] if admin_line else []),
        "",
        "## Attack success rate (ASR@k_max) per cell",
        "",
        summary_md,
        "",
    ]
    for sid in scenarios:
        md += [
            f"## {sid}",
            "",
            f"![KM survival — {sid}](km_{sid}.png)",
            "",
            f"![ASR heatmap — {sid}](asr_heatmap_{sid}.png)",
            "",
        ]
    if logrank_df is not None and not logrank_df.empty:
        n_missing = int((logrank_df.get("status") == "NOT_COLLECTED").sum()) \
            if "status" in logrank_df else 0
        note = ("_Declared and locked before any of this data was collected. Non-significance "
                "≠ equivalence; comparisons are flagged `underpowered` at small N. The full "
                "locked declaration and the disposition of every hypothesis are in "
                "[docs/PREREGISTRATION.md](../../docs/PREREGISTRATION.md)._")
        if n_missing:
            note += (f"\n\n_{n_missing} pre-registered pair(s) are marked `NOT_COLLECTED`: they "
                     "name a model absent from this dataset. They were declared, not dropped._")
        md += ["## Pre-registered log-rank tests",
               "",
               note,
               "",
               _df_to_markdown(logrank_df),
               ""]
    (Path(out_dir) / "REPORT.md").write_text("\n".join(md), encoding="utf-8")


def _df_to_markdown(df) -> str:
    cols = list(df.columns)
    header = "| " + " | ".join(cols) + " |"
    sep = "|" + "|".join(["---"] * len(cols)) + "|"
    rows = []
    for _, r in df.iterrows():
        rows.append("| " + " | ".join(
            (f"{r[c]:.4g}" if isinstance(r[c], float) else str(r[c])) for c in cols
        ) + " |")
    return "\n".join([header, sep, *rows])
