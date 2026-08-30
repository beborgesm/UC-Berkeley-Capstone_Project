"""Survival-analysis tests: KM formulas, lifelines cross-check, bootstrap, log-rank,
report artifacts, and the reliability stub."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from breachbench.analysis import (
    analyze_and_report,
    asr_heatmap_matrix,
    asr_table,
    bootstrap_survival,
    kaplan_meier,
    load_cell_observations,
    logrank_test,
)
from breachbench.analysis.reliability import cohen_kappa_judge_vs_human
from breachbench.config.schema import AttackVector, ModelSpec, Vendor
from breachbench.loop import Cell, execute_run
from breachbench.recording import RoundsCsvWriter, run_result_to_rows
from breachbench.scenarios import load_scenarios

from tests.conftest import attacker_stub, leaky_target_stub, make_config, stubborn_target_stub

SCENARIOS = load_scenarios()


def test_km_hand_computed_example():
    # durations/events: two breaches at k=2, one at k=4, one censored at k=5.
    durations = np.array([2, 2, 4, 5])
    events = np.array([1, 1, 1, 0])
    km = kaplan_meier(durations, events, k_max=5)
    np.testing.assert_allclose(km.survival, [1.0, 0.5, 0.5, 0.25, 0.25])
    assert km.asr_at_kmax == pytest.approx(0.75)
    # Greenwood at k=4.
    assert km.greenwood_var[3] == pytest.approx(0.25 ** 2 * 0.75)
    # cloglog band brackets the estimate.
    assert (km.ci_lower <= km.survival + 1e-9).all()
    assert (km.survival <= km.ci_upper + 1e-9).all()
    assert (km.ci_lower >= -1e-9).all() and (km.ci_upper <= 1 + 1e-9).all()


def test_km_matches_lifelines():
    lifelines = pytest.importorskip("lifelines")
    rng = np.random.default_rng(0)
    durations = rng.integers(1, 11, size=40)
    events = rng.integers(0, 2, size=40)
    km = kaplan_meier(durations, events, k_max=10)

    kmf = lifelines.KaplanMeierFitter().fit(durations, event_observed=events)
    for i, k in enumerate(km.k):
        assert km.survival[i] == pytest.approx(float(kmf.predict(k)), abs=1e-9)


def test_bootstrap_shapes_and_bounds():
    durations = np.array([2, 3, 3, 5, 5, 5])
    events = np.array([1, 1, 0, 1, 0, 0])
    bs = bootstrap_survival(durations, events, k_max=5, B=500, seed=1)
    assert bs.survival_lower.shape == (5,)
    assert (bs.survival_lower <= bs.survival_upper + 1e-9).all()
    assert 0.0 <= bs.asr_kmax_lower <= bs.asr_kmax_upper <= 1.0


def test_logrank_identical_groups_not_significant():
    d = np.array([2, 3, 4, 5, 5])
    e = np.array([1, 1, 1, 0, 0])
    res = logrank_test(d, e, d.copy(), e.copy(), k_max=5)
    assert res.chi2 == pytest.approx(0.0, abs=1e-9)
    assert res.p_value > 0.99
    assert res.underpowered is True  # tiny N


def test_logrank_separated_groups_significant():
    # Group A breaches early every run; group B never breaches.
    rng = np.random.default_rng(0)
    a_dur = np.full(60, 2); a_ev = np.ones(60, dtype=int)
    b_dur = np.full(60, 10); b_ev = np.zeros(60, dtype=int)
    res = logrank_test(a_dur, a_ev, b_dur, b_ev, k_max=10)
    assert res.chi2 > 10
    assert res.p_value < 0.01
    assert res.underpowered is False


def _write_rounds(tmp_path):
    cfg = make_config(scenarios=["conf_vault_v1"],
                      vectors=[AttackVector.ROLEPLAY, AttackVector.CIPHER], k_max=6)
    writer = RoundsCsvWriter(tmp_path / "rounds.csv")
    scenario = SCENARIOS["conf_vault_v1"]
    # ROLEPLAY: leaks at round 2 (high ASR). CIPHER: never leaks (censored).
    plan = [
        (AttackVector.ROLEPLAY, lambda: leaky_target_stub(2), 5),
        (AttackVector.CIPHER, stubborn_target_stub, 5),
    ]
    for vector, target_factory, reps in plan:
        cell = Cell(target=ModelSpec(vendor=Vendor.STUB, model_version="target-y"),
                    scenario_id="conf_vault_v1", attack_vector=vector)
        for rep in range(reps):
            result = execute_run(
                cell=cell, repetition_index=rep, scenario=scenario, config=cfg,
                attacker_provider=attacker_stub(), target_provider=target_factory(),
            )
            writer.append_rows(run_result_to_rows(result, config=cfg, scenario=scenario))
    return cfg, tmp_path / "rounds.csv"


def test_asr_table_and_heatmap(tmp_path):
    cfg, rounds_csv = _write_rounds(tmp_path)
    cells = load_cell_observations(rounds_csv)
    table = asr_table(cells, cfg.k_max, bootstrap_B=200)
    assert set(table["attack_vector"]) == {"ROLEPLAY", "CIPHER"}
    roleplay = table[table["attack_vector"] == "ROLEPLAY"].iloc[0]
    cipher = table[table["attack_vector"] == "CIPHER"].iloc[0]
    assert roleplay["asr_at_kmax"] == pytest.approx(1.0)  # leaks every run
    assert cipher["asr_at_kmax"] == pytest.approx(0.0)  # never leaks
    assert "asr_kmax_ci_lower" in table.columns

    heat = asr_heatmap_matrix(table, "conf_vault_v1")
    # Columns are the RESOLVED model-version string that was actually logged.
    assert "stub/target" in heat.columns
    assert set(heat.index) == {"ROLEPLAY", "CIPHER"}


def test_analyze_and_report_writes_artifacts(tmp_path):
    cfg, rounds_csv = _write_rounds(tmp_path)
    out = tmp_path / "analysis"
    summary = analyze_and_report(rounds_csv, out, config=cfg, bootstrap_B=200)
    assert (out / "survival_curves.csv").exists()
    assert (out / "asr_table.csv").exists()
    assert (out / "asr_heatmap_conf_vault_v1.csv").exists()
    assert "ASR@k_max" in summary
    # Survival curve is a proper non-increasing function.
    curves = pd.read_csv(out / "survival_curves.csv")
    for _, grp in curves.groupby("cell_id"):
        s = grp.sort_values("k")["survival"].to_numpy()
        assert all(a >= b - 1e-9 for a, b in zip(s, s[1:]))


def test_logrank_pairs_matched_by_cell_id_despite_resolved_version_drift(tmp_path):
    # Two distinct configured targets whose adapters report the SAME resolved version
    # must still match their pre-registered log-rank pair (matched on cell_id).
    from breachbench.config.schema import ExperimentConfig, LogrankPair
    from breachbench.analysis.report import _run_logrank_pairs

    writer = RoundsCsvWriter(tmp_path / "rounds.csv")
    scenario = SCENARIOS["conf_vault_v1"]
    model_a = ModelSpec(vendor=Vendor.STUB, model_version="target-A")
    model_b = ModelSpec(vendor=Vendor.STUB, model_version="target-B")
    cfg = ExperimentConfig(
        master_seed=1, k_max=5, repetitions=4, partial_min=8,
        attacker=ModelSpec(vendor=Vendor.STUB, model_version="attacker-x"),
        targets=[model_a, model_b],
        scenarios=["conf_vault_v1"], vectors=[AttackVector.ROLEPLAY],
        logrank_pairs=[LogrankPair(scenario_id="conf_vault_v1",
                                   attack_vector=AttackVector.ROLEPLAY,
                                   model_a=model_a, model_b=model_b)],
    )
    for model, leak in [(model_a, 2), (model_b, 4)]:
        cell = Cell(target=model, scenario_id="conf_vault_v1", attack_vector=AttackVector.ROLEPLAY)
        for rep in range(4):
            result = execute_run(cell=cell, repetition_index=rep, scenario=scenario, config=cfg,
                                 attacker_provider=attacker_stub(),
                                 target_provider=leaky_target_stub(leak))
            writer.append_rows(run_result_to_rows(result, config=cfg, scenario=scenario))

    cells = load_cell_observations(tmp_path / "rounds.csv")
    logrank_df = _run_logrank_pairs(cells, cfg)
    assert (logrank_df["status"] == "OK").all()
    assert logrank_df.iloc[0]["n_a"] == 4 and logrank_df.iloc[0]["n_b"] == 4


def test_round_sig_absorbs_cross_platform_float_noise():
    # logrank.csv's p-value passes through scipy's chi2 survival function, and pyproject.toml
    # pins no scipy upper bound — so a routine scipy patch release (or a different BLAS backend
    # on CI's Linux runner vs a dev machine's macOS Accelerate) can shift its last 1-2
    # significant digits. That turned a scientifically-identical result into a spurious CI
    # failure (git diff on the full-precision CSV). _round_sig is the fix: verify it rounds to
    # the requested significant figures regardless of magnitude, and is a no-op on edge values.
    from breachbench.analysis.report import _round_sig

    assert _round_sig(38.77645987375795, 8) == 38.77646
    assert _round_sig(4.75224437956336e-10, 8) == 4.7522444e-10
    # Two values differing only past the 8th significant figure (the actual observed drift)
    # must round to the same result.
    assert _round_sig(4.75224437956336e-10, 8) == _round_sig(4.75224441123e-10, 8)
    assert _round_sig(0.0, 8) == 0.0
    assert _round_sig(float("nan"), 8) != _round_sig(float("nan"), 8)  # NaN passes through as-is


def test_reliability_is_a_stub():
    with pytest.raises(NotImplementedError):
        cohen_kappa_judge_vs_human("rounds.csv", "gold.csv")
