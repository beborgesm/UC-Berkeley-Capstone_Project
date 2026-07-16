"""Offline test of the pilot gate: all-vector sweep, per-cell breakdown, artifact
persistence, and advisories (stub providers, no network)."""

from __future__ import annotations

import pandas as pd

from breachbench.config.schema import AttackVector, ModelSpec, Vendor
from breachbench.runner.pilot import run_pilot, select_pilot_target
from breachbench.scenarios import load_scenarios

from tests.conftest import (
    attacker_stub,
    firing_target_by_round,
    leaky_target_by_round,
    make_config,
    stubborn_target_stub,
)

SCENARIOS = load_scenarios()


def _factory(target_factory):
    """attacker spec -> attacker stub; any target spec -> one shared target stub
    (mirrors production: one provider instance reused across runs)."""
    shared = {}

    def factory(spec: ModelSpec):
        if spec.model_version == "attacker-x":
            return attacker_stub()
        if "target" not in shared:
            shared["target"] = target_factory()
        return shared["target"]

    return factory


def test_pilot_default_target_is_last_roster_entry():
    cfg = make_config(targets=[
        ModelSpec(vendor=Vendor.STUB, model_version="strong"),
        ModelSpec(vendor=Vendor.STUB, model_version="weak-last"),
    ])
    assert select_pilot_target(cfg, None).model_version == "weak-last"
    # Explicit override via "vendor:model".
    assert select_pilot_target(cfg, "stub:strong").model_version == "strong"


def test_pilot_sweeps_all_vectors_and_both_scenarios():
    cfg = make_config(scenarios=["conf_vault_v1", "integ_override_v1"],
                      vectors=[AttackVector.ROLEPLAY, AttackVector.CIPHER,
                               AttackVector.AUTHORITY, AttackVector.MANY_SHOT],
                      k_max=8)
    report = run_pilot(cfg, scenarios=SCENARIOS, n=2,
                       provider_factory=_factory(lambda: leaky_target_by_round(3)))
    # 4 vectors x 2 scenarios = 8 cells.
    assert len(report.cells) == 8
    assert {c.attack_vector for c in report.cells} == {"ROLEPLAY", "CIPHER", "AUTHORITY", "MANY_SHOT"}
    # Confidentiality cells breach (leaky target); integrity cells censor (no tool fire).
    conf_cells = [c for c in report.cells if c.scenario_id == "conf_vault_v1"]
    assert all(c.breaches == c.n for c in conf_cells)
    assert report.breach_round_distribution == {3: len(conf_cells) * 2}
    assert report.breaches_all_at_round_one is False


def test_pilot_integrity_breaches_by_round():
    cfg = make_config(scenarios=["conf_vault_v1", "integ_override_v1"],
                      vectors=[AttackVector.AUTHORITY], k_max=6)
    report = run_pilot(cfg, scenarios=SCENARIOS, n=3,
                       provider_factory=_factory(lambda: firing_target_by_round(2)))
    # The pilot always runs one confidentiality + one integrity cell; pick the integrity one.
    integ = next(c for c in report.cells if c.breach_type == "INTEGRITY")
    assert integ.breaches == 3
    assert set(integ.breach_rounds) == {2}


def test_pilot_zero_breach_advisory():
    cfg = make_config(scenarios=["conf_vault_v1"], vectors=[AttackVector.ROLEPLAY], k_max=5)
    report = run_pilot(cfg, scenarios=SCENARIOS, n=3,
                       provider_factory=_factory(stubborn_target_stub))
    assert report.breaches == 0
    assert "zero breaches" in report.format()


def test_pilot_persists_artifacts(tmp_path):
    cfg = make_config(scenarios=["conf_vault_v1", "integ_override_v1"],
                      vectors=[AttackVector.ROLEPLAY], k_max=5)
    report = run_pilot(cfg, scenarios=SCENARIOS, n=2, output_dir=tmp_path / "pilot",
                       provider_factory=_factory(lambda: leaky_target_by_round(2)))
    rounds_csv = tmp_path / "pilot" / "pilot_rounds.csv"
    assert rounds_csv.exists()
    df = pd.read_csv(rounds_csv)
    assert "event_observed" not in df.columns  # raw round file never carries the KM event col
    # Transcripts written per run.
    assert list((tmp_path / "pilot" / "runs").glob("*.jsonl"))
    assert report.output_dir is not None
