"""Survival encoding + recording tests (the Kaplan–Meier input contract)."""

from __future__ import annotations

import pandas as pd

from breachbench.config.schema import AttackVector, ModelSpec, Vendor
from breachbench.loop import Cell, execute_run
from breachbench.recording import (
    COLUMNS,
    RoundsCsvWriter,
    TranscriptStore,
    rounds_df_to_run_summary,
    run_result_to_rows,
)
from breachbench.scenarios import load_scenarios

from tests.conftest import (
    attacker_stub,
    firing_target_stub,
    leaky_target_stub,
    make_config,
    stubborn_target_stub,
)

SCENARIOS = load_scenarios()
TARGET = ModelSpec(vendor=Vendor.STUB, model_version="target-y")


def _cell(scenario_id: str) -> Cell:
    return Cell(target=TARGET, scenario_id=scenario_id, attack_vector=AttackVector.ROLEPLAY)


def _run(scenario_id, target_provider, k_max=5, rep=0):
    cfg = make_config(k_max=k_max)
    scenario = SCENARIOS[scenario_id]
    result = execute_run(
        cell=_cell(scenario_id),
        repetition_index=rep,
        scenario=scenario,
        config=cfg,
        attacker_provider=attacker_stub(),
        target_provider=target_provider,
    )
    rows = run_result_to_rows(result, config=cfg, scenario=scenario)
    return result, rows


def test_rows_have_exact_schema_columns():
    _, rows = _run("conf_vault_v1", leaky_target_stub(2))
    for row in rows:
        assert set(row.keys()) == set(COLUMNS)


def test_rounds_csv_has_no_round_level_event_observed_column():
    # The KM footgun column must NOT exist in the raw round schema.
    assert "event_observed" not in COLUMNS
    assert "run_event_observed" in COLUMNS
    assert "breach_this_round" in COLUMNS


def test_breach_encoding_k_star():
    result, rows = _run("conf_vault_v1", leaky_target_stub(3), k_max=6)
    # Run-level trio on the terminal row.
    terminal = [r for r in rows if r["is_terminal_round"] == 1][0]
    assert terminal["duration_rounds"] == 3
    assert terminal["run_event_observed"] == 1
    assert terminal["censored"] == 0
    assert terminal["termination_reason"] == "BREACH_CONFIDENTIALITY"
    # Only the breaching (terminal) round is flagged as a per-round breach.
    breaches = [r for r in rows if r["breach_this_round"] == 1]
    assert len(breaches) == 1
    assert breaches[0]["round_index"] == 3


def test_censored_encoding_kmax():
    _, rows = _run("conf_vault_v1", stubborn_target_stub(), k_max=4)
    terminal = [r for r in rows if r["is_terminal_round"] == 1][0]
    assert terminal["duration_rounds"] == 4
    assert terminal["run_event_observed"] == 0
    assert terminal["censored"] == 1
    assert terminal["termination_reason"] == "BUDGET_EXHAUSTED"
    assert all(r["breach_this_round"] == 0 for r in rows)


def test_integrity_tool_columns_populated():
    _, rows = _run("integ_override_v1", firing_target_stub(2), k_max=5)
    terminal = [r for r in rows if r["is_terminal_round"] == 1][0]
    assert terminal["override_tool_fired"] == 1
    assert terminal["tool_fire_detection"] == "NATIVE_TOOL_CALL"
    assert terminal["run_event_observed"] == 1
    # Confidentiality columns are inert for an integrity scenario.
    assert terminal["canary_leaked"] == 0
    assert terminal["canary_match_method"] == "NONE"


def test_run_summary_projection_renames_event_and_is_km_ready(tmp_path):
    # Write two runs (one breach, one censored) to rounds.csv, then project.
    cfg = make_config(k_max=5)
    writer = RoundsCsvWriter(tmp_path / "rounds.csv")
    for rep, (scenario_id, tgt) in enumerate([
        ("conf_vault_v1", leaky_target_stub(2)),
        ("conf_vault_v1", stubborn_target_stub()),
    ]):
        scenario = SCENARIOS[scenario_id]
        result = execute_run(
            cell=_cell(scenario_id),
            repetition_index=rep,
            scenario=scenario,
            config=cfg,
            attacker_provider=attacker_stub(),
            target_provider=tgt,
        )
        writer.append_rows(run_result_to_rows(result, config=cfg, scenario=scenario))

    rounds = pd.read_csv(tmp_path / "rounds.csv")
    assert "event_observed" not in rounds.columns  # raw file must not carry it

    summary = rounds_df_to_run_summary(rounds)
    # Exactly one KM event column, one row per run.
    assert "event_observed" in summary.columns
    assert "run_event_observed" not in summary.columns
    assert len(summary) == rounds["run_id"].nunique()

    # Every duration is in {1..k_max}; events are 0/1.
    assert summary["duration_rounds"].between(1, cfg.k_max).all()
    assert summary["event_observed"].isin([0, 1]).all()


def test_lifelines_fits_run_summary_without_reshaping(tmp_path):
    lifelines = _import_lifelines()
    if lifelines is None:
        import pytest

        pytest.skip("lifelines not installed (optional [analysis] extra)")

    cfg = make_config(k_max=5)
    writer = RoundsCsvWriter(tmp_path / "rounds.csv")
    targets = [leaky_target_stub(2), leaky_target_stub(4), stubborn_target_stub()]
    for rep, tgt in enumerate(targets):
        scenario = SCENARIOS["conf_vault_v1"]
        result = execute_run(
            cell=_cell("conf_vault_v1"),
            repetition_index=rep,
            scenario=scenario,
            config=cfg,
            attacker_provider=attacker_stub(),
            target_provider=tgt,
        )
        writer.append_rows(run_result_to_rows(result, config=cfg, scenario=scenario))

    summary = rounds_df_to_run_summary(pd.read_csv(tmp_path / "rounds.csv"))
    km = lifelines.KaplanMeierFitter()
    km.fit(summary["duration_rounds"], event_observed=summary["event_observed"])
    # Survival is a proper, non-increasing function bounded in [0, 1].
    sf = km.survival_function_.values.flatten()
    assert (sf <= 1.0 + 1e-9).all() and (sf >= -1e-9).all()
    assert all(earlier >= later - 1e-9 for earlier, later in zip(sf, sf[1:]))


def test_transcript_store_writes_jsonl(tmp_path):
    result, _ = _run("conf_vault_v1", leaky_target_stub(2), k_max=5)
    store = TranscriptStore(tmp_path / "runs")
    path = store.write_run(result)
    assert path.exists()
    lines = path.read_text().strip().splitlines()
    assert len(lines) == len(result.rounds)


def _import_lifelines():
    try:
        import lifelines

        return lifelines
    except Exception:
        return None
