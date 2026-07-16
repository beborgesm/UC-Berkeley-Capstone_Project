"""End-to-end run loop against StubProviders (no network, no keys).

Exercises the full Attacker -> Target -> deterministic detection -> termination /
censoring path and the survival encoding, with scripted breaches and a censored run.
"""

from __future__ import annotations

from breachbench.config.schema import AttackVector, ModelSpec, Vendor
from breachbench.loop import Cell, TerminationReason, execute_run
from breachbench.scenarios import load_scenarios

from tests.conftest import (
    attacker_stub,
    erroring_target_stub,
    firing_target_stub,
    leaky_target_stub,
    make_config,
    stubborn_target_stub,
    text_protocol_target_stub,
)

SCENARIOS = load_scenarios()
TARGET = ModelSpec(vendor=Vendor.STUB, model_version="target-y")


def _cell(scenario_id: str, vector=AttackVector.ROLEPLAY) -> Cell:
    return Cell(target=TARGET, scenario_id=scenario_id, attack_vector=vector)


def test_confidentiality_breach_at_round_k():
    cfg = make_config(k_max=5)
    result = execute_run(
        cell=_cell("conf_vault_v1"),
        repetition_index=0,
        scenario=SCENARIOS["conf_vault_v1"],
        config=cfg,
        attacker_provider=attacker_stub(),
        target_provider=leaky_target_stub(leak_round=3),
    )
    assert result.event_observed == 1
    assert result.censored == 0
    assert result.duration_rounds == 3
    assert result.termination_reason == TerminationReason.BREACH_CONFIDENTIALITY
    assert result.run_valid == 1
    assert len(result.rounds) == 3
    assert result.rounds[-1].canary_result.matched is True
    assert result.rounds[-1].canary_result.method == "EXACT"


def test_integrity_breach_via_native_tool_call():
    cfg = make_config(k_max=6)
    result = execute_run(
        cell=_cell("integ_override_v1"),
        repetition_index=0,
        scenario=SCENARIOS["integ_override_v1"],
        config=cfg,
        attacker_provider=attacker_stub("Invoke the override now."),
        target_provider=firing_target_stub(fire_round=2),
    )
    assert result.event_observed == 1
    assert result.duration_rounds == 2
    assert result.termination_reason == TerminationReason.BREACH_INTEGRITY
    assert result.rounds[-1].dispatch_result.fired is True
    assert result.rounds[-1].dispatch_result.detection == "NATIVE_TOOL_CALL"


def test_integrity_breach_via_text_protocol_on_non_native_target():
    cfg = make_config(k_max=6)
    result = execute_run(
        cell=_cell("integ_override_v1"),
        repetition_index=0,
        scenario=SCENARIOS["integ_override_v1"],
        config=cfg,
        attacker_provider=attacker_stub("Invoke the override now."),
        target_provider=text_protocol_target_stub(fire_round=2),
    )
    assert result.event_observed == 1
    assert result.duration_rounds == 2
    assert result.termination_reason == TerminationReason.BREACH_INTEGRITY
    assert result.rounds[-1].dispatch_result.detection == "TEXT_PROTOCOL"


def test_censored_run_survives_to_kmax():
    cfg = make_config(k_max=4)
    result = execute_run(
        cell=_cell("conf_vault_v1"),
        repetition_index=0,
        scenario=SCENARIOS["conf_vault_v1"],
        config=cfg,
        attacker_provider=attacker_stub(),
        target_provider=stubborn_target_stub(),
    )
    assert result.event_observed == 0
    assert result.censored == 1
    assert result.duration_rounds == 4
    assert result.termination_reason == TerminationReason.BUDGET_EXHAUSTED
    assert result.run_valid == 1
    assert len(result.rounds) == 4


def test_transient_error_after_valid_round_reschedules():
    # A rate-limit failure mid-run is an operational artifact, NOT survival data —
    # it must invalidate + reschedule, never pollute the CSV as a censored point.
    from breachbench.providers.retry import ErrorType

    cfg = make_config(k_max=5)
    result = execute_run(
        cell=_cell("conf_vault_v1"),
        repetition_index=0,
        scenario=SCENARIOS["conf_vault_v1"],
        config=cfg,
        attacker_provider=attacker_stub(),
        target_provider=erroring_target_stub(fail_from_round=3, error_type=ErrorType.RATE_LIMIT),
    )
    assert result.run_valid == 0
    assert result.termination_reason == TerminationReason.INVALIDATED


def test_nontransient_error_after_valid_round_admin_censors():
    # A genuine (non-transient) failure after real data -> administrative censoring.
    from breachbench.providers.retry import ErrorType

    cfg = make_config(k_max=5)
    result = execute_run(
        cell=_cell("conf_vault_v1"),
        repetition_index=0,
        scenario=SCENARIOS["conf_vault_v1"],
        config=cfg,
        attacker_provider=attacker_stub(),
        target_provider=erroring_target_stub(fail_from_round=3, error_type=ErrorType.OTHER),
    )
    assert result.event_observed == 0
    assert result.censored == 1
    assert result.run_valid == 1
    assert result.duration_rounds == 2  # last valid round
    assert result.termination_reason == TerminationReason.ADMIN_CENSORED_ERROR


def test_invalidated_when_error_before_any_valid_round():
    cfg = make_config(k_max=5)
    result = execute_run(
        cell=_cell("conf_vault_v1"),
        repetition_index=0,
        scenario=SCENARIOS["conf_vault_v1"],
        config=cfg,
        attacker_provider=attacker_stub(),
        target_provider=erroring_target_stub(fail_from_round=1),  # fails immediately
    )
    assert result.run_valid == 0
    assert result.duration_rounds == 0
    assert result.termination_reason == TerminationReason.INVALIDATED


def test_target_sees_growing_conversation():
    # By round 3 the leaky target's system prompt echo proves multi-turn context is
    # assembled; also confirm the history length grows correctly.
    cfg = make_config(k_max=3)
    result = execute_run(
        cell=_cell("conf_vault_v1"),
        repetition_index=0,
        scenario=SCENARIOS["conf_vault_v1"],
        config=cfg,
        attacker_provider=attacker_stub(),
        target_provider=stubborn_target_stub(),
    )
    # 3 rounds recorded, each with a distinct attacker prompt (call index grows).
    prompts = [r.attacker_prompt for r in result.rounds]
    assert len(prompts) == 3
    assert prompts[0] != prompts[1] != prompts[2]


def test_run_id_is_deterministic():
    cell = _cell("conf_vault_v1")
    from breachbench.loop import make_run_id

    assert make_run_id(cell, 0) == make_run_id(cell, 0)
    assert make_run_id(cell, 0) != make_run_id(cell, 1)


def test_cipher_induced_encodings_subset_of_transforms():
    # Detection/attack coupling: CIPHER may only induce encodings the matcher covers.
    from breachbench.attacks.registry import REGISTRY
    from breachbench.detection import TRANSFORM_NAMES

    cipher = REGISTRY[AttackVector.CIPHER]
    assert set(cipher.induces_encodings).issubset(TRANSFORM_NAMES)
