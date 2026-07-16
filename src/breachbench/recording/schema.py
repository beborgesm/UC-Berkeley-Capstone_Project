"""Authoritative rounds.csv schema + row projection from a RunResult.

One row per round. Run-level survival fields (duration_rounds, run_event_observed,
censored, termination_reason, run_valid) are constant within a run and backfilled
onto every round row; `is_terminal_round` marks the final round.

DELIBERATELY ABSENT: a round-level `event_observed` column. It would duplicate
`breach_this_round` and invites a wrong KM curve if fit against the raw round file
(duration is run-constant, breach is round-local). The single unambiguous KM event
column exists only after projection to run_summary.csv (see run_summary.py).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from .. import SCHEMA_VERSION
from ..config.schema import BreachType, ExperimentConfig
from ..scenarios.schema import ScenarioSpec

if TYPE_CHECKING:
    from ..loop.types import RoundResult, RunResult

# Ordered, authoritative column list for rounds.csv.
COLUMNS: tuple[str, ...] = (
    # --- identity / reproducibility ---
    "schema_version",
    "run_id",
    "cell_id",
    "repetition_index",
    "round_index",
    "timestamp_utc",
    "target_vendor",
    "target_model_version",
    "attacker_vendor",
    "attacker_model_version",
    "judge_vendor",
    "judge_model_version",
    "master_seed",
    "run_seed",
    "canary_seed",
    "target_temperature",
    "attacker_temperature",
    "judge_temperature",
    # --- experimental cell ---
    "scenario_id",
    "breach_type_targeted",
    "attack_vector",
    # --- deterministic outcomes (PRIMARY) ---
    "canary_leaked",
    "canary_match_method",
    "canary_partial_match",
    "canary_partial_run_len",
    "canary_transform_name",
    "canary_matched_value",
    "override_tool_fired",
    "tool_fire_detection",
    "tool_call_arguments",
    "breach_this_round",
    # --- Judge outputs (SECONDARY, non-authoritative) ---
    "judge_invoked",
    "judge_verdict",
    "judge_degradation_score",
    "judge_rationale",
    "judge_authoritative",
    # --- operational hygiene ---
    "api_status",
    "error_flag",
    "error_type",
    "truncated",
    "target_latency_ms",
    "attacker_latency_ms",
    "judge_latency_ms",
    "retry_count",
    # --- run-level survival fields (constant within run) ---
    "is_terminal_round",
    "duration_rounds",
    "run_event_observed",
    "censored",
    "termination_reason",
    "run_valid",
    # --- transcript pointer ---
    "transcript_ref",
)


def _canary_cells(rr: "RoundResult") -> dict[str, Any]:
    cr = rr.canary_result
    if cr is None:
        return {
            "canary_leaked": 0,
            "canary_match_method": "NONE",
            "canary_partial_match": 0,
            "canary_partial_run_len": 0,
            "canary_transform_name": "",
            "canary_matched_value": "",
        }
    return {
        "canary_leaked": int(cr.matched),
        "canary_match_method": cr.method,
        "canary_partial_match": int(cr.partial_match),
        "canary_partial_run_len": cr.partial_run_len,
        "canary_transform_name": cr.transform_name or "",
        "canary_matched_value": cr.matched_value or "",
    }


def _tool_cells(rr: "RoundResult") -> dict[str, Any]:
    dr = rr.dispatch_result
    if dr is None:
        return {
            "override_tool_fired": 0,
            "tool_fire_detection": "NONE",
            "tool_call_arguments": "",
        }
    return {
        "override_tool_fired": int(dr.fired),
        "tool_fire_detection": dr.detection,
        "tool_call_arguments": json.dumps(dr.arguments) if dr.arguments else "",
    }


def _judge_cells(rr: "RoundResult", config: ExperimentConfig) -> dict[str, Any]:
    jr = rr.judge_result
    if jr is None:
        return {
            "judge_invoked": 0,
            "judge_verdict": "",
            "judge_degradation_score": "",
            "judge_rationale": "",
            "judge_authoritative": 0,
        }
    # jr is a JudgeResult (duck-typed to avoid importing judge here).
    return {
        "judge_invoked": 1,
        "judge_verdict": getattr(jr, "verdict", ""),
        "judge_degradation_score": getattr(jr, "degradation_score", ""),
        "judge_rationale": getattr(jr, "rationale", ""),
        "judge_authoritative": int(bool(getattr(jr, "authoritative", False))),
    }


def run_result_to_rows(
    result: "RunResult",
    *,
    config: ExperimentConfig,
    scenario: ScenarioSpec,
    judge_model_version: str = "",
) -> list[dict[str, Any]]:
    """Project a RunResult into one rounds.csv row per round."""
    n = len(result.rounds)
    judge_vendor = config.judge.vendor.value if config.judge.enabled else ""
    breach_type = scenario.breach_type.value
    rows: list[dict[str, Any]] = []

    for idx, rr in enumerate(result.rounds):
        is_terminal = idx == n - 1
        tr = rr.target_response
        ar = rr.attacker_response
        row: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "run_id": result.run_id,
            "cell_id": result.cell.cell_id(),
            "repetition_index": result.repetition_index,
            "round_index": rr.round_index,
            "timestamp_utc": rr.timestamp_utc,
            "target_vendor": result.cell.target.vendor.value,
            "target_model_version": tr.resolved_model_version,
            "attacker_vendor": config.attacker.vendor.value,
            "attacker_model_version": ar.resolved_model_version or result.attacker_model_version,
            "judge_vendor": judge_vendor,
            "judge_model_version": judge_model_version,
            "master_seed": config.master_seed,
            "run_seed": result.run_seed,
            "canary_seed": result.canary_seed,
            "target_temperature": config.temperatures.target,
            "attacker_temperature": config.temperatures.attacker,
            "judge_temperature": config.temperatures.judge,
            "scenario_id": result.cell.scenario_id,
            "breach_type_targeted": breach_type,
            "attack_vector": result.cell.attack_vector.value,
            **_canary_cells(rr),
            **_tool_cells(rr),
            "breach_this_round": int(rr.breach_this_round),
            **_judge_cells(rr, config),
            "api_status": tr.http_status if tr.http_status is not None else "",
            "error_flag": int(rr.error_flag),
            "error_type": rr.error_type,
            "truncated": int(tr.truncated),
            "target_latency_ms": round(tr.latency_ms, 3),
            "attacker_latency_ms": round(ar.latency_ms, 3),
            "judge_latency_ms": "",
            "retry_count": tr.retries,
            "is_terminal_round": int(is_terminal),
            "duration_rounds": result.duration_rounds,
            "run_event_observed": result.event_observed,
            "censored": result.censored,
            "termination_reason": result.termination_reason.value,
            "run_valid": result.run_valid,
            "transcript_ref": f"{result.run_id}#{rr.round_index}",
        }
        rows.append(row)
    return rows


# Columns projected into run_summary.csv (one row per run). The KM event column is
# `run_event_observed` renamed to `event_observed` — the ONLY place that name exists.
RUN_SUMMARY_COLUMNS: tuple[str, ...] = (
    "run_id",
    "cell_id",
    "target_vendor",
    "target_model_version",
    "scenario_id",
    "breach_type_targeted",
    "attack_vector",
    "repetition_index",
    "duration_rounds",
    "event_observed",  # <- renamed from run_event_observed on projection
    "censored",
    "termination_reason",
    "run_valid",
)
