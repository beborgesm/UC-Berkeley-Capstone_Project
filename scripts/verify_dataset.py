#!/usr/bin/env python
"""Integrity check for the published dataset in data/.

Everything in data/ was collected against live endpoints that no longer answer, so it can
never be regenerated. This script is the guard: it asserts the published files still say what
the documentation claims, and fails loudly if they drift. It runs offline in ~2 seconds and is
wired into CI, so a bad merge or a stray edit to a CSV cannot pass silently.

    python scripts/verify_dataset.py            # check, print a report
    python scripts/verify_dataset.py --quiet    # exit code only

Exit 0 = every check passed. Exit 1 = at least one FAIL.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from breachbench.analysis.labels import prettify_model  # noqa: E402
from breachbench.recording.run_summary import rounds_df_to_run_summary  # noqa: E402

DATA = ROOT / "data"

# ── Expected state of the published benchmark ────────────────────────────────────────────
# 3 targets x 2 scenarios x 4 vectors x 20 repetitions, k_max = 10.
EXPECTED = {
    "models": {"gpt-3.5-turbo", "gpt-4o-mini", "gpt-5-nano"},
    "cells": 24,
    "runs": 480,
    "rounds": 3424,
    "breaches": 181,
    "censored": 299,
    "reps_per_cell": 20,
    "raw_runs": 523,
    "judge_rows": 960,
}

# The 24 transcripts with no row in rounds_raw.csv. These are NOT missing data: they are the
# runs that were in flight when the shared OpenAI account hit its billing wall (every one ends
# in a 429 `insufficient_quota`). A rate-limit is a TRANSIENT failure, so the amended
# operational rule invalidated and rescheduled them instead of recording them as survival data
# — the reschedule never happened because the key stayed dead. They ship as evidence that the
# harness discarded infrastructure failures rather than logging them as "the model held".
# See docs/PREREGISTRATION.md §3B and DEVELOPMENT_TIMELINE.md Phase 6-7.
EXPECTED_ORPHANS = {
    "8f8230fc1b192931": 17,  # gpt-4-turbo · conf_vault_v1 · CIPHER   (reps 3-19)
    "d34e81ad052c6377": 7,   # gpt-4-turbo · conf_vault_v1 · MANY_SHOT (reps 0-6)
}


class Checker:
    def __init__(self, quiet: bool = False) -> None:
        self.quiet, self.failures = quiet, 0

    def section(self, title: str) -> None:
        if not self.quiet:
            print(f"\n\033[1m{title}\033[0m")

    def check(self, label: str, actual, expected=None, *, ok: bool | None = None) -> bool:
        passed = (actual == expected) if ok is None else ok
        if not passed:
            self.failures += 1
        if not self.quiet:
            mark = "\033[32m✓\033[0m" if passed else "\033[31m✗\033[0m"
            detail = f"{actual}" if expected is None or passed else f"{actual} (expected {expected})"
            print(f"  {mark} {label:<46} {detail}")
        return passed

    def note(self, text: str) -> None:
        if not self.quiet:
            print(f"    \033[2m{text}\033[0m")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    c = Checker(args.quiet)

    # ── files present ────────────────────────────────────────────────────────────────────
    c.section("Files")
    required = ["rounds_raw.csv", "rounds_benchmark.csv", "judge_scores.csv", "ledger.jsonl"]
    for name in required:
        c.check(f"data/{name}", (DATA / name).exists(), True)
    tdir = DATA / "transcripts"
    c.check("data/transcripts/", tdir.is_dir(), True)
    if c.failures:
        print("\n\033[31mFAIL\033[0m — required files missing; nothing else can be checked.")
        return 1

    bench = pd.read_csv(DATA / "rounds_benchmark.csv", low_memory=False)
    raw = pd.read_csv(DATA / "rounds_raw.csv", low_memory=False)
    summary = rounds_df_to_run_summary(bench)

    # ── the benchmark grid ───────────────────────────────────────────────────────────────
    c.section("Benchmark grid (data/rounds_benchmark.csv)")
    models = {prettify_model(m) for m in bench["target_model_version"].unique()}
    c.check("target models", models, EXPECTED["models"])
    c.check("cells", bench["cell_id"].nunique(), EXPECTED["cells"])
    c.check("runs", bench["run_id"].nunique(), EXPECTED["runs"])
    c.check("rounds", len(bench), EXPECTED["rounds"])

    per_cell = sorted({int(n) for n in summary.groupby("cell_id").size()})
    c.check(f"every cell has N={EXPECTED['reps_per_cell']}", per_cell,
            [EXPECTED["reps_per_cell"]])

    # ── survival outcomes ────────────────────────────────────────────────────────────────
    c.section("Survival outcomes")
    breaches = int(summary["event_observed"].sum())
    censored = int(len(summary) - breaches)
    c.check("breaches (events)", breaches, EXPECTED["breaches"])
    c.check("censored (held to k_max)", censored, EXPECTED["censored"])
    c.check("all runs valid (run_valid == 1)", int((summary["run_valid"] != 1).sum()), 0)

    reasons = summary["termination_reason"].value_counts().to_dict()
    admin = int(reasons.get("ADMIN_CENSORED_ERROR", 0))
    c.check("ADMIN_CENSORED_ERROR runs", admin, 0)
    c.note("every censored run is a genuine survival to k_max, not an operational failure")
    c.check("termination reasons", set(reasons),
            {"BREACH_CONFIDENTIALITY", "BREACH_INTEGRITY", "BUDGET_EXHAUSTED"})

    # A round-level event column in the raw file is the KM footgun the schema exists to avoid.
    c.check("no round-level `event_observed` column",
            "event_observed" not in bench.columns, True)
    c.check("k_max never exceeded", int(summary["duration_rounds"].max()), 10)

    # ── raw superset ─────────────────────────────────────────────────────────────────────
    c.section("Raw collection (data/rounds_raw.csv)")
    c.check("runs", raw["run_id"].nunique(), EXPECTED["raw_runs"])
    c.check("benchmark is a subset of raw",
            set(bench["run_id"]).issubset(set(raw["run_id"])), True)
    extra = sorted({prettify_model(m) for m in raw["target_model_version"].unique()} - EXPECTED["models"])
    c.check("extra (partial) targets beyond the benchmark", extra, ["gpt-4-turbo"])
    c.note("declared but only partially collected — see docs/PREREGISTRATION.md")

    # ── transcripts ──────────────────────────────────────────────────────────────────────
    c.section("Transcripts (data/transcripts/)")
    files = {p.stem for p in tdir.glob("*.jsonl")}
    raw_ids = set(raw["run_id"])
    missing = raw_ids - files
    c.check("every recorded run has a transcript", len(missing), 0)
    if missing:
        c.note(f"missing: {sorted(missing)[:5]}")

    orphans = files - raw_ids
    by_cell: dict[str, int] = {}
    for o in orphans:
        by_cell[o.split("-")[0]] = by_cell.get(o.split("-")[0], 0) + 1
    c.check("orphan transcripts (documented)", by_cell, EXPECTED_ORPHANS)
    c.note("in-flight runs killed by the billing wall; discarded by the transient-failure")
    c.note("rule rather than recorded as survival data (pre-registration §3B)")
    c.check("transcript files total", len(files), len(raw_ids) + sum(EXPECTED_ORPHANS.values()))

    # Spot-check one transcript's shape so the documented schema stays true.
    sample = json.loads(next(iter(sorted(tdir.glob("*.jsonl")))).read_text().splitlines()[0])
    c.check("transcript record shape",
            {"round_index", "attacker_prompt", "target_text", "detection"} <= set(sample), True)

    # ── secondary Judge ──────────────────────────────────────────────────────────────────
    c.section("Secondary Judge sample (data/judge_scores.csv)")
    judge = pd.read_csv(DATA / "judge_scores.csv")
    c.check("scored rounds", len(judge), EXPECTED["judge_rows"])
    coverage = len(judge) / len(bench)
    c.check(f"coverage of benchmark rounds ({coverage:.0%})", 0.25 <= coverage <= 0.32, True)
    c.note("a balanced SAMPLE, not a census — free-tier Gemini quota; see docs/LIMITATIONS.md")
    c.check("judge rows all join to benchmark runs",
            set(judge["run_id"]).issubset(set(bench["run_id"])), True)
    c.check("verdict vocabulary", set(judge["verdict"]),
            {"NO_DEGRADATION", "PERSONA_BREAK", "WEAK_REFUSAL"})
    per_model = judge["target_model_version"].map(prettify_model).value_counts()
    c.check("all 3 models sampled", set(per_model.index), EXPECTED["models"])
    c.note(f"per-model rows: {per_model.to_dict()}")

    # ── verdict ──────────────────────────────────────────────────────────────────────────
    if not args.quiet:
        print()
    if c.failures:
        print(f"\033[31mFAIL\033[0m — {c.failures} check(s) failed.")
        return 1
    print("\033[32mPASS\033[0m — published dataset matches the documented state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
