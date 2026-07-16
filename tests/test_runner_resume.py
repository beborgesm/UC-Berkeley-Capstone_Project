"""Runner tests: grid enumeration, Attacker!=Target guard, and resumability.

All offline against StubProviders (no network, no keys).
"""

from __future__ import annotations

import pandas as pd

from breachbench.config.schema import AttackVector, ModelSpec, Vendor
from breachbench.runner import enumerate_cells, enumerate_runs, run_experiment
from breachbench.scenarios import load_scenarios

from tests.conftest import attacker_stub, leaky_target_stub, make_config, stubborn_target_stub

SCENARIOS = load_scenarios()


def _provider_factory(target_stub_factory):
    """Return a factory mapping the attacker spec -> attacker stub and any target
    spec -> a freshly-scripted target stub."""

    def factory(spec: ModelSpec):
        if spec.vendor == Vendor.STUB and spec.model_version == "attacker-x":
            return attacker_stub()
        return target_stub_factory()

    return factory


def test_grid_skips_self_attack_cells():
    # Attacker == one of the targets -> those cells are skipped.
    attacker = ModelSpec(vendor=Vendor.STUB, model_version="shared")
    cfg = make_config(
        attacker=attacker,
        targets=[attacker, ModelSpec(vendor=Vendor.STUB, model_version="other")],
        scenarios=["conf_vault_v1"],
        vectors=[AttackVector.ROLEPLAY, AttackVector.CIPHER],
    )
    plan = enumerate_cells(cfg)
    assert len(plan.skipped_self_attack) == 2  # 1 scenario x 2 vectors for the shared target
    assert all(c.target == attacker for c in plan.skipped_self_attack)
    assert all(c.target != attacker for c in plan.cells)


def test_run_count_matches_grid():
    cfg = make_config(
        scenarios=["conf_vault_v1", "integ_override_v1"],
        vectors=[AttackVector.ROLEPLAY, AttackVector.CIPHER],
        repetitions=3,
    )
    runs = enumerate_runs(cfg)
    # 1 target x 2 scenarios x 2 vectors x 3 reps = 12
    assert len(runs) == 12


def test_full_sweep_writes_csv_transcripts_and_summary(tmp_path):
    cfg = make_config(
        scenarios=["conf_vault_v1"],
        vectors=[AttackVector.ROLEPLAY, AttackVector.AUTHORITY],
        repetitions=4,
        k_max=5,
    )
    report = run_experiment(
        cfg,
        scenarios=SCENARIOS,
        provider_factory=_provider_factory(lambda: leaky_target_stub(2)),
        output_dir=tmp_path / "out",
        transcript_dir=tmp_path / "out" / "runs",
    )
    assert report.planned_runs == 8  # 2 vectors x 4 reps
    assert report.executed == 8
    assert report.breached == 8  # leaky target breaches every run

    rounds = pd.read_csv(report.paths.rounds_csv)
    assert rounds["run_id"].nunique() == 8
    summary = pd.read_csv(report.paths.run_summary_csv)
    assert len(summary) == 8
    assert "event_observed" in summary.columns
    assert "event_observed" not in rounds.columns

    # One transcript file per run.
    transcript_files = list((tmp_path / "out" / "runs").glob("*.jsonl"))
    assert len(transcript_files) == 8


def test_resume_skips_completed_runs(tmp_path):
    cfg = make_config(
        scenarios=["conf_vault_v1"],
        vectors=[AttackVector.ROLEPLAY],
        repetitions=5,
        k_max=4,
    )
    out = tmp_path / "out"

    # First pass executes all 5 runs.
    r1 = run_experiment(
        cfg, scenarios=SCENARIOS,
        provider_factory=_provider_factory(stubborn_target_stub),
        output_dir=out, transcript_dir=out / "runs",
    )
    assert r1.executed == 5
    assert r1.skipped_existing == 0

    # Second pass: everything already complete -> all skipped, no new rows.
    rows_before = len(pd.read_csv(out / "rounds.csv"))
    r2 = run_experiment(
        cfg, scenarios=SCENARIOS,
        provider_factory=_provider_factory(stubborn_target_stub),
        output_dir=out, transcript_dir=out / "runs",
    )
    assert r2.executed == 0
    assert r2.skipped_existing == 5
    rows_after = len(pd.read_csv(out / "rounds.csv"))
    assert rows_after == rows_before  # no duplicate rows on resume


def test_resume_recovers_from_csv_when_ledger_lost(tmp_path):
    # Simulates a hard power-off where run rows were written but the ledger entry
    # never landed: delete the ledger entirely, then resume. Reconciliation from
    # rounds.csv must treat those runs as complete -> no re-run, no duplicate rows.
    cfg = make_config(scenarios=["conf_vault_v1"], vectors=[AttackVector.ROLEPLAY],
                      repetitions=4, k_max=4)
    out = tmp_path / "out"
    run_experiment(cfg, scenarios=SCENARIOS,
                   provider_factory=_provider_factory(stubborn_target_stub),
                   output_dir=out, transcript_dir=out / "runs")
    rows_before = len(pd.read_csv(out / "rounds.csv"))

    # Wipe the ledger — as if mark_complete never persisted.
    (out / "ledger.jsonl").unlink()

    r2 = run_experiment(cfg, scenarios=SCENARIOS,
                        provider_factory=_provider_factory(stubborn_target_stub),
                        output_dir=out, transcript_dir=out / "runs")
    assert r2.executed == 0            # everything recovered from the CSV
    assert r2.skipped_existing == 4
    assert len(pd.read_csv(out / "rounds.csv")) == rows_before  # no duplicate rows


def test_ledger_reconcile_direct(tmp_path):
    from breachbench.runner.ledger import Ledger

    # Minimal rounds.csv with one terminal row for a run.
    csv = tmp_path / "rounds.csv"
    csv.write_text("run_id,is_terminal_round\nabc-0001,1\nabc-0001,0\n")
    ledger = Ledger(tmp_path / "ledger.jsonl")
    assert ledger.is_complete("abc-0001") is False
    recovered = ledger.reconcile_with_rounds(csv)
    assert recovered == 1
    assert ledger.is_complete("abc-0001") is True
    # Idempotent: a second reconcile recovers nothing new.
    assert ledger.reconcile_with_rounds(csv) == 0


def test_run_summary_dedupes_duplicate_terminal_rows():
    from breachbench.recording.run_summary import rounds_df_to_run_summary

    # Two identical terminal rows for one run (as a resumed dup would produce).
    base = {
        "is_terminal_round": 1, "run_id": "r1", "cell_id": "c1",
        "target_vendor": "stub", "target_model_version": "m", "scenario_id": "s",
        "breach_type_targeted": "CONFIDENTIALITY", "attack_vector": "ROLEPLAY",
        "repetition_index": 0, "duration_rounds": 3, "run_event_observed": 1,
        "censored": 0, "termination_reason": "BREACH_CONFIDENTIALITY", "run_valid": 1,
    }
    df = pd.DataFrame([base, dict(base)])  # duplicated
    summary = rounds_df_to_run_summary(df)
    assert len(summary) == 1
    assert summary.iloc[0]["event_observed"] == 1


def test_vendor_filter_restricts_roster():
    from breachbench.cli import _filter_targets

    cfg = make_config(
        attacker=ModelSpec(vendor=Vendor.STUB, model_version="atk"),
        targets=[ModelSpec(vendor=Vendor.OPENAI, model_version="gpt-4o-mini"),
                 ModelSpec(vendor=Vendor.GROQ, model_version="llama-3.1-8b-instant")],
        scenarios=["conf_vault_v1"], vectors=[AttackVector.ROLEPLAY],
    )
    only_openai = _filter_targets(cfg, "openai", None)
    assert [t.label() for t in only_openai.targets] == ["openai:gpt-4o-mini"]
    by_label = _filter_targets(cfg, None, "groq:llama-3.1-8b-instant")
    assert [t.label() for t in by_label.targets] == ["groq:llama-3.1-8b-instant"]


def test_stub_reproducibility_structure_identical(tmp_path):
    # Same config + same StubProviders -> byte-identical rounds.csv (structure
    # reproducibility for the offline provider only).
    cfg = make_config(scenarios=["conf_vault_v1"], vectors=[AttackVector.ROLEPLAY],
                      repetitions=3, k_max=4)

    def run_once(dirname):
        out = tmp_path / dirname
        run_experiment(
            cfg, scenarios=SCENARIOS,
            provider_factory=_provider_factory(stubborn_target_stub),
            output_dir=out, transcript_dir=out / "runs",
        )
        df = pd.read_csv(out / "rounds.csv")
        # Drop volatile columns (wall-clock timestamp, measured latencies).
        return df.drop(columns=["timestamp_utc", "target_latency_ms",
                                "attacker_latency_ms"])

    a = run_once("a")
    b = run_once("b")
    pd.testing.assert_frame_equal(a, b)
