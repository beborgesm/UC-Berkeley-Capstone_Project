"""Deterministic, resumable experiment orchestrator.

Iterates the full grid (targets × scenarios × vectors × repetitions) in a fixed
order, executing each run sequentially (free-tier-safe) and writing rounds.csv +
JSONL transcripts + a ledger. Re-running skips completed run_ids (resumable) and
reschedules invalidated runs. After the sweep it regenerates run_summary.csv.

Determinism scope: seed derivation, cell/rep enumeration, canary generation, and
control flow are reproducible. Live LLM responses are NOT — that is expected.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..config.schema import ExperimentConfig, ModelSpec, ModelsRegistry
from ..loop.run import execute_run, make_run_id
from ..loop.types import Cell, RunResult, TerminationReason
from ..providers.base import ChatProvider
from ..providers.registry import build_provider
from ..recording.csv_writer import RoundsCsvWriter
from ..recording.run_summary import write_run_summary_csv
from ..recording.schema import run_result_to_rows
from ..recording.transcript import TranscriptStore
from ..scenarios.loader import load_scenarios_by_ids
from ..scenarios.schema import ScenarioSpec
from .grid import enumerate_cells, enumerate_runs
from .ledger import Ledger

logger = logging.getLogger("breachbench.runner")

ProviderFactory = Callable[[ModelSpec], ChatProvider]


@dataclass
class ExperimentPaths:
    output_dir: Path
    transcript_dir: Path

    @property
    def rounds_csv(self) -> Path:
        return self.output_dir / "rounds.csv"

    @property
    def run_summary_csv(self) -> Path:
        return self.output_dir / "run_summary.csv"

    @property
    def ledger_path(self) -> Path:
        return self.output_dir / "ledger.jsonl"


@dataclass
class ExperimentReport:
    planned_runs: int = 0
    executed: int = 0
    skipped_existing: int = 0
    skipped_self_attack_cells: int = 0
    breached: int = 0
    censored: int = 0
    invalidated: int = 0
    paths: ExperimentPaths | None = None
    per_termination: dict[str, int] = field(default_factory=dict)


def _build_judge(config: ExperimentConfig, provider_factory: ProviderFactory):
    """Construct a single-judge panel from config (panel-ready for later)."""
    from ..judge.base import JudgePanel
    from ..judge.llm_judge import LLMJudge

    judge_spec = ModelSpec(vendor=config.judge.vendor, model_version=config.judge.model_version)
    judge_provider = provider_factory(judge_spec)
    judge = JudgePanel([
        LLMJudge(
            provider=judge_provider,
            model_version=config.judge.model_version,
            temperature=config.temperatures.judge,
        )
    ])
    return judge, config.judge.model_version


def _default_provider_factory(
    config: ExperimentConfig, models_registry: ModelsRegistry | None
) -> ProviderFactory:
    cache: dict[str, ChatProvider] = {}

    def factory(spec: ModelSpec) -> ChatProvider:
        key = spec.label()
        if key not in cache:
            cache[key] = build_provider(spec, models_registry=models_registry, retry=config.retry)
        return cache[key]

    return factory


def run_experiment(
    config: ExperimentConfig,
    *,
    scenarios: dict[str, ScenarioSpec] | None = None,
    models_registry: ModelsRegistry | None = None,
    provider_factory: ProviderFactory | None = None,
    output_dir: str | Path | None = None,
    transcript_dir: str | Path | None = None,
    judge: object | None = None,
    judge_model_version: str = "",
) -> ExperimentReport:
    scenarios = scenarios or load_scenarios_by_ids(config.scenarios)
    provider_factory = provider_factory or _default_provider_factory(config, models_registry)

    paths = ExperimentPaths(
        output_dir=Path(output_dir or config.output.dir),
        transcript_dir=Path(transcript_dir or config.output.transcript_dir),
    )
    paths.output_dir.mkdir(parents=True, exist_ok=True)

    ledger = Ledger(paths.ledger_path)
    # Power-off safety: any run already fully written to rounds.csv counts as done,
    # even if the ledger didn't record it — so resume never re-runs / duplicates it.
    recovered = ledger.reconcile_with_rounds(paths.rounds_csv)
    if recovered:
        logger.info("reconciled %d completed run(s) from existing rounds.csv", recovered)
    writer = RoundsCsvWriter(paths.rounds_csv)
    transcripts = TranscriptStore(paths.transcript_dir)

    plan = enumerate_cells(config)
    for cell in plan.skipped_self_attack:
        ledger.mark_skipped(cell.cell_id(), "attacker_equals_target",
                            {"target": cell.target.label()})

    attacker_provider = provider_factory(config.attacker)

    # Build the (secondary) Judge from config when enabled and not injected.
    if judge is None and config.judge.enabled:
        judge, judge_model_version = _build_judge(config, provider_factory)

    report = ExperimentReport(paths=paths)
    report.skipped_self_attack_cells = len(plan.skipped_self_attack)

    runs = enumerate_runs(config)
    report.planned_runs = len(runs)

    for cell, rep in runs:
        run_id = make_run_id(cell, rep)
        if ledger.is_complete(run_id):
            report.skipped_existing += 1
            continue

        scenario = scenarios[cell.scenario_id]
        target_provider = provider_factory(cell.target)
        result: RunResult = execute_run(
            cell=cell,
            repetition_index=rep,
            scenario=scenario,
            config=config,
            attacker_provider=attacker_provider,
            target_provider=target_provider,
            judge=judge,
        )

        # Always persist the transcript (idempotent, keyed by run_id) for audit.
        transcripts.write_run(result)

        if result.run_valid == 0:
            # Invalidated before any valid round -> do NOT record to rounds.csv and
            # do NOT mark complete; it reschedules on the next invocation.
            report.invalidated += 1
            logger.warning("run %s invalidated (%s) — will reschedule",
                          run_id, result.termination_reason.value)
            continue

        rows = run_result_to_rows(
            result, config=config, scenario=scenario, judge_model_version=judge_model_version
        )
        writer.append_rows(rows)
        ledger.mark_complete(run_id, {
            "termination_reason": result.termination_reason.value,
            "duration_rounds": result.duration_rounds,
            "event_observed": result.event_observed,
        })

        report.executed += 1
        report.per_termination[result.termination_reason.value] = (
            report.per_termination.get(result.termination_reason.value, 0) + 1
        )
        if result.event_observed == 1:
            report.breached += 1
        elif result.termination_reason in (
            TerminationReason.BUDGET_EXHAUSTED,
            TerminationReason.ADMIN_CENSORED_ERROR,
        ):
            report.censored += 1

    # Regenerate the KM-ready per-run summary from the authoritative round file.
    if paths.rounds_csv.exists():
        write_run_summary_csv(paths.rounds_csv, paths.run_summary_csv)

    return report
