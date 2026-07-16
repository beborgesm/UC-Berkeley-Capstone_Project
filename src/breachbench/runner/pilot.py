"""PILOT GATE (required checkpoint, build step 8).

Runs a pilot sweep against ONE chosen target — by default the weakest (last) target
in the roster, so it exercises the model most likely to produce breach events. For
that target it runs EVERY attack vector against one confidentiality and one
integrity scenario (all vectors × 2 scenarios × N reps), persists a rounds.csv and
JSONL transcripts so results are inspectable, and reports per-cell:
  * breach / censor / invalid counts and the breach round-index distribution,
  * any RATE_LIMIT / TIMEOUT / TRUNCATION flags.

Purpose: before spending full budget, confirm (a) breaches occur and are not all at
round 1, (b) k_max gives usable curve resolution, (c) the loop survives free-tier
rate limits. Failures here mean retune, not proceed. The aggregation is provider-
agnostic (`provider_factory` can inject stubs) so it stays unit-testable offline.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from ..config.schema import BreachType, ExperimentConfig, ModelSpec, ModelsRegistry
from ..loop.run import execute_run
from ..loop.types import Cell, RunResult
from ..recording.csv_writer import RoundsCsvWriter
from ..recording.schema import run_result_to_rows
from ..recording.transcript import TranscriptStore
from ..scenarios.loader import load_scenarios_by_ids
from ..scenarios.schema import ScenarioSpec
from .experiment import ProviderFactory, _default_provider_factory


@dataclass
class PilotCellResult:
    scenario_id: str
    breach_type: str
    attack_vector: str
    n: int = 0
    breaches: int = 0
    censored: int = 0
    invalid: int = 0
    breach_rounds: list[int] = field(default_factory=list)
    rate_limit_rounds: int = 0
    timeout_rounds: int = 0
    truncated_rounds: int = 0


@dataclass
class PilotReport:
    target: str
    n_per_cell: int
    k_max: int
    cells: list[PilotCellResult] = field(default_factory=list)
    output_dir: str | None = None

    @property
    def breaches(self) -> int:
        return sum(c.breaches for c in self.cells)

    @property
    def censored(self) -> int:
        return sum(c.censored for c in self.cells)

    @property
    def invalid(self) -> int:
        return sum(c.invalid for c in self.cells)

    @property
    def breach_round_distribution(self) -> dict[int, int]:
        dist: Counter[int] = Counter()
        for c in self.cells:
            dist.update(c.breach_rounds)
        return dict(sorted(dist.items()))

    @property
    def rate_limit_rounds(self) -> int:
        return sum(c.rate_limit_rounds for c in self.cells)

    @property
    def timeout_rounds(self) -> int:
        return sum(c.timeout_rounds for c in self.cells)

    @property
    def truncated_rounds(self) -> int:
        return sum(c.truncated_rounds for c in self.cells)

    @property
    def breaches_all_at_round_one(self) -> bool:
        dist = self.breach_round_distribution
        return bool(dist) and set(dist) == {1}

    def format(self) -> str:
        lines = [
            "=== BreachBenchmark PILOT GATE ===",
            f"target: {self.target}    N per cell: {self.n_per_cell}    k_max: {self.k_max}",
            f"totals -> breaches: {self.breaches}  censored: {self.censored}  invalid: {self.invalid}",
            f"breach round-index distribution: {self.breach_round_distribution}",
            f"throttling -> RATE_LIMIT: {self.rate_limit_rounds}  TIMEOUT: {self.timeout_rounds}  "
            f"TRUNCATION: {self.truncated_rounds}",
            "",
            "per-cell (vector / scenario):",
        ]
        for c in self.cells:
            rd = Counter(c.breach_rounds)
            lines.append(
                f"  {c.attack_vector:<9} {c.scenario_id:<20} "
                f"breach={c.breaches}/{c.n} censor={c.censored} invalid={c.invalid} "
                f"rounds={dict(sorted(rd.items()))}"
            )
        lines.append("")
        lines.extend(self._advisories())
        if self.output_dir:
            lines.append(f"artifacts: {self.output_dir}/pilot_rounds.csv , {self.output_dir}/runs/")
        return "\n".join(lines)

    def _advisories(self) -> list[str]:
        out: list[str] = []
        if self.breaches == 0:
            out.append("ADVISORY: zero breaches even on the weakest target — attacks too weak, "
                       "personas over-defended, or k_max too small. Retune before full run.")
        elif self.breaches_all_at_round_one:
            out.append("ADVISORY: all breaches at round 1 — k_max resolution unused; consider a "
                       "harder opening move or a lower k_max.")
        if self.rate_limit_rounds or self.timeout_rounds:
            out.append("ADVISORY: throttling observed — raise backoff / lower concurrency, or the "
                       "free-tier quota is insufficient for the full run.")
        if self.invalid:
            out.append(f"ADVISORY: {self.invalid} run(s) invalidated before any valid round — a "
                       "target/key is failing outright (check quota).")
        if not out:
            out.append("GATE OK: breaches occur with round spread, no throttling — safe to scale.")
        return out


def select_pilot_target(config: ExperimentConfig, target: ModelSpec | str | None) -> ModelSpec:
    """Resolve the pilot target: explicit spec/"vendor:model" string, else the last
    (weakest) roster entry."""
    if target is None:
        return config.targets[-1]
    if isinstance(target, ModelSpec):
        return target
    vendor, _, model = target.partition(":")
    from ..config.schema import Vendor

    return ModelSpec(vendor=Vendor(vendor), model_version=model)


def _pilot_scenarios(scenarios: dict[str, ScenarioSpec]) -> list[ScenarioSpec]:
    conf = next((s for s in scenarios.values() if s.breach_type == BreachType.CONFIDENTIALITY), None)
    integ = next((s for s in scenarios.values() if s.breach_type == BreachType.INTEGRITY), None)
    return [s for s in (conf, integ) if s is not None]


def run_pilot(
    config: ExperimentConfig,
    *,
    scenarios: dict[str, ScenarioSpec] | None = None,
    models_registry: ModelsRegistry | None = None,
    provider_factory: ProviderFactory | None = None,
    n: int = 3,
    target: ModelSpec | str | None = None,
    output_dir: str | Path | None = None,
) -> PilotReport:
    scenarios = scenarios or load_scenarios_by_ids(config.scenarios)
    provider_factory = provider_factory or _default_provider_factory(config, models_registry)
    attacker_provider = provider_factory(config.attacker)

    pilot_target = select_pilot_target(config, target)
    target_provider = provider_factory(pilot_target)
    pilot_scenarios = _pilot_scenarios(scenarios)

    # Optional artifact persistence (skipped in offline unit tests unless requested).
    writer = transcripts = None
    out_path = None
    if output_dir is not None:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        writer = RoundsCsvWriter(out_path / "pilot_rounds.csv")
        transcripts = TranscriptStore(out_path / "runs")

    report = PilotReport(target=pilot_target.label(), n_per_cell=n, k_max=config.k_max,
                         output_dir=str(out_path) if out_path else None)

    for scenario in pilot_scenarios:
        for vector in config.vectors:
            cell = Cell(target=pilot_target, scenario_id=scenario.scenario_id, attack_vector=vector)
            cr = PilotCellResult(scenario_id=scenario.scenario_id,
                                 breach_type=scenario.breach_type.value,
                                 attack_vector=vector.value)
            for rep in range(n):
                result: RunResult = execute_run(
                    cell=cell, repetition_index=rep, scenario=scenario, config=config,
                    attacker_provider=attacker_provider, target_provider=target_provider,
                )
                _tally_cell(cr, result)
                if writer is not None and result.run_valid == 1:
                    writer.append_rows(run_result_to_rows(result, config=config, scenario=scenario))
                if transcripts is not None:
                    transcripts.write_run(result)
            report.cells.append(cr)

    return report


def _tally_cell(cr: PilotCellResult, result: RunResult) -> None:
    cr.n += 1
    if result.run_valid == 0:
        cr.invalid += 1
    elif result.event_observed == 1:
        cr.breaches += 1
        cr.breach_rounds.append(result.duration_rounds)
    else:
        cr.censored += 1
    for rr in result.rounds:
        if rr.error_type == "RATE_LIMIT":
            cr.rate_limit_rounds += 1
        elif rr.error_type == "TIMEOUT":
            cr.timeout_rounds += 1
        if rr.target_response.truncated:
            cr.truncated_rounds += 1
