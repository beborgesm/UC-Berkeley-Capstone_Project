"""Run orchestration: an ordered sequence of rounds against one cell, terminating
on breach or on exhausting k_max, recorded as a single survival trial.

Termination / censoring (§3.2, §3.3):
  * breach at k*        -> event_observed=1, censored=0, duration=k*
  * survived k_max      -> event_observed=0, censored=1, duration=k_max (right-censored)
  * persistent op error -> ADMIN_CENSORED_ERROR (censored at last valid round) OR,
                           if it failed before ANY valid round, INVALIDATED
                           (run_valid=0, excluded — reschedule). Never a fabricated
                           survival outcome.
"""

from __future__ import annotations

from ..config.schema import BreachType, ExperimentConfig
from ..detection.tool_dispatch import MockToolDispatcher
from ..providers.base import ChatProvider
from ..scenarios.canary import render_target
from ..scenarios.schema import ScenarioSpec
from ..attacks.attacker import Attacker, build_grey_box_brief
from ..attacks.base import Turn
from ..attacks.registry import get_meta
from .round import RunContext, execute_round, forbidden_tool_to_spec, text_protocol_brief
from .types import (
    Cell,
    RoundResult,
    RunResult,
    TerminationReason,
    derive_canary_seed,
    derive_run_seed,
)


# Operational error types that must reschedule (not be recorded as censored data).
_TRANSIENT_ERRORS = {"RATE_LIMIT", "CONNECTION", "TIMEOUT"}


def make_run_id(cell: Cell, repetition_index: int) -> str:
    return f"{cell.cell_id()}-{repetition_index:04d}"


def build_run_context(
    *,
    cell: Cell,
    scenario: ScenarioSpec,
    config: ExperimentConfig,
    attacker_provider: ChatProvider,
    target_provider: ChatProvider,
    run_seed: int,
    canary_seed: int,
    dispatcher: MockToolDispatcher | None = None,
    judge: object | None = None,
) -> RunContext:
    rendered = render_target(scenario, canary_seed=canary_seed)
    brief = build_grey_box_brief(scenario, config.k_max)
    strategy = get_meta(cell.attack_vector).strategy
    attacker = Attacker(
        provider=attacker_provider,
        model_version=config.attacker.model_version,
        strategy=strategy,
        brief=brief,
        temperature=config.temperatures.attacker,
        seed=run_seed,
    )

    # Native tool-calling where the target supports it; otherwise fall back to the
    # strict text-protocol (augment the system prompt, send no native tools).
    tool_spec = forbidden_tool_to_spec(scenario)
    system_prompt = rendered.system_prompt
    tools = None
    if tool_spec is not None:
        if getattr(target_provider, "supports_native_tools", True):
            tools = [tool_spec]
        else:
            system_prompt = system_prompt + text_protocol_brief(scenario)

    return RunContext(
        cell=cell,
        scenario=scenario,
        rendered=rendered,
        system_prompt=system_prompt,
        attacker=attacker,
        target_provider=target_provider,
        dispatcher=dispatcher or MockToolDispatcher(),
        partial_min=config.partial_min,
        target_temperature=config.temperatures.target,
        run_seed=run_seed,
        timeout_s=config.retry.timeout_s,
        tools=tools,
        judge=judge,
    )


def execute_run(
    *,
    cell: Cell,
    repetition_index: int,
    scenario: ScenarioSpec,
    config: ExperimentConfig,
    attacker_provider: ChatProvider,
    target_provider: ChatProvider,
    dispatcher: MockToolDispatcher | None = None,
    judge: object | None = None,
) -> RunResult:
    run_seed = derive_run_seed(config.master_seed, cell.cell_id(), repetition_index)
    canary_seed = derive_canary_seed(run_seed)
    ctx = build_run_context(
        cell=cell,
        scenario=scenario,
        config=config,
        attacker_provider=attacker_provider,
        target_provider=target_provider,
        run_seed=run_seed,
        canary_seed=canary_seed,
        dispatcher=dispatcher,
        judge=judge,
    )

    result = RunResult(
        run_id=make_run_id(cell, repetition_index),
        cell=cell,
        repetition_index=repetition_index,
        run_seed=run_seed,
        canary_seed=canary_seed,
        canary=ctx.rendered.canary,
        attacker_model_version=config.attacker.model_version,
    )

    history: list[Turn] = []
    last_valid_round = 0

    for k in range(1, config.k_max + 1):
        rr: RoundResult = execute_round(ctx, k, history)
        result.rounds.append(rr)
        history.append((rr.attacker_prompt, rr.target_response.text))

        # Operational failure on the Target call -> administrative handling.
        if not rr.valid:
            if last_valid_round == 0 or rr.error_type in _TRANSIENT_ERRORS:
                # No valid data yet, OR a transient/throttling failure (rate limit, network,
                # timeout). These are operational artifacts, NOT the model surviving — do
                # NOT record them as a censored observation (that would pollute the survival
                # curves). Invalidate and reschedule so the cell gets a clean, complete run.
                _finalize_invalidated(result)
            else:
                # A non-transient failure after real data -> genuine administrative censoring.
                _finalize_admin_censored(result, last_valid_round)
            return result

        last_valid_round = k

        if rr.breach_this_round:
            _finalize_breach(result, scenario, k)
            return result

    _finalize_survived(result, config.k_max)
    return result


# ---- finalizers --------------------------------------------------------------
def _finalize_breach(result: RunResult, scenario: ScenarioSpec, k: int) -> None:
    result.duration_rounds = k
    result.event_observed = 1
    result.censored = 0
    result.run_valid = 1
    result.termination_reason = (
        TerminationReason.BREACH_CONFIDENTIALITY
        if scenario.breach_type == BreachType.CONFIDENTIALITY
        else TerminationReason.BREACH_INTEGRITY
    )


def _finalize_survived(result: RunResult, k_max: int) -> None:
    result.duration_rounds = k_max
    result.event_observed = 0
    result.censored = 1
    result.run_valid = 1
    result.termination_reason = TerminationReason.BUDGET_EXHAUSTED


def _finalize_admin_censored(result: RunResult, last_valid_round: int) -> None:
    # Censored at the last valid round; kept in the analysis as administrative
    # right-censoring, never coerced into a breach/survival value.
    result.duration_rounds = last_valid_round
    result.event_observed = 0
    result.censored = 1
    result.run_valid = 1
    result.termination_reason = TerminationReason.ADMIN_CENSORED_ERROR


def _finalize_invalidated(result: RunResult) -> None:
    # Failed before any valid round -> excluded from survival analysis; reschedule.
    result.duration_rounds = 0
    result.event_observed = 0
    result.censored = 1
    result.run_valid = 0
    result.termination_reason = TerminationReason.INVALIDATED
