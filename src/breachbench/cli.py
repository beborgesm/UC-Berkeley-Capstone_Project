"""Command-line entry points: run the full experiment, the pilot gate, or analysis.

Config loads lazily; keys are only checked when a live command actually needs them.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config.loader import (
    DEFAULT_EXPERIMENT_PATH,
    DEFAULT_MODELS_PATH,
    load_experiment_config,
    load_models_registry,
)
from .config.schema import ExperimentConfig, ModelsRegistry
from .config.settings import has_api_key


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _load(config_path: str | None, models_path: str | None):
    config = load_experiment_config(config_path or DEFAULT_EXPERIMENT_PATH)
    registry = load_models_registry(models_path or DEFAULT_MODELS_PATH)
    return config, registry


def _filter_targets(
    config: ExperimentConfig, vendors: str | None, targets: str | None
) -> ExperimentConfig:
    """Return a config restricted to a subset of the target roster. cell_ids are
    derived from the target spec, so a filtered run accumulates into the SAME
    resumable output as any other filter — this is how the tiered rollout works."""
    keep = list(config.targets)
    if vendors:
        wanted = {v.strip().lower() for v in vendors.split(",") if v.strip()}
        keep = [t for t in keep if t.vendor.value in wanted]
    if targets:
        wanted_labels = {t.strip() for t in targets.split(",") if t.strip()}
        keep = [t for t in keep if t.label() in wanted_labels]
    if not keep:
        raise SystemExit(f"ERROR: target filter (vendors={vendors!r}, targets={targets!r}) "
                         f"matched no roster entries.")
    return config.model_copy(update={"targets": keep})


def missing_key_vendors(config: ExperimentConfig, registry: ModelsRegistry) -> list[str]:
    """Vendors used by this config whose API key env var is absent."""
    used = {config.attacker.vendor, *(t.vendor for t in config.targets)}
    if config.judge.enabled:
        used.add(config.judge.vendor)
    missing: list[str] = []
    for vendor in used:
        if vendor.value not in registry.vendors:
            continue  # STUB or unregistered — nothing to check
        env = registry.entry(vendor).api_key_env
        if not has_api_key(env):
            missing.append(f"{vendor.value} ({env})")
    return sorted(missing)


def run_experiment_cli(argv: list[str] | None = None) -> int:
    from .runner.experiment import run_experiment

    parser = _base_parser("Run the full BreachBenchmark grid")
    parser.add_argument("--repetitions", type=int, default=None,
                        help="override N per cell (e.g. --repetitions 1 for a cheap full-grid smoke)")
    parser.add_argument("--vendors", default=None,
                        help="only run targets from these vendors (comma-sep, e.g. openai,groq) "
                             "— enables a tiered rollout into the SAME resumable output")
    parser.add_argument("--targets", default=None,
                        help="only run these targets (comma-sep 'vendor:model_version')")
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)
    config, registry = _load(args.config, args.models)
    if args.repetitions is not None:
        config = config.model_copy(update={"repetitions": args.repetitions})
    if args.vendors or args.targets:
        config = _filter_targets(config, args.vendors, args.targets)
        print(f"target subset: {[t.label() for t in config.targets]}")

    missing = missing_key_vendors(config, registry)
    if missing and not args.allow_missing_keys:
        print(f"ERROR: missing API keys for: {', '.join(missing)}", file=sys.stderr)
        print("Set them (see .env.example) or pass --allow-missing-keys to proceed.", file=sys.stderr)
        return 2

    report = run_experiment(config, models_registry=registry,
                            output_dir=args.output_dir)
    print(f"planned={report.planned_runs} executed={report.executed} "
          f"skipped_existing={report.skipped_existing} "
          f"breached={report.breached} censored={report.censored} "
          f"invalidated={report.invalidated} "
          f"self_attack_cells_skipped={report.skipped_self_attack_cells}")
    print(f"outputs: {report.paths.rounds_csv} , {report.paths.run_summary_csv}")
    return 0


def pilot_cli(argv: list[str] | None = None) -> int:
    from .runner.pilot import run_pilot

    parser = _base_parser("Run the required PILOT GATE before scaling")
    parser.add_argument("-n", "--n", type=int, default=3, help="repetitions per pilot cell")
    parser.add_argument("--target", default=None,
                        help="pilot target as 'vendor:model_version' (default: weakest/last roster entry)")
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)
    config, registry = _load(args.config, args.models)

    # The pilot only touches the chosen target's vendor + the attacker's vendor;
    # only require those keys (not the whole roster).
    from .config.schema import Vendor
    from .runner.pilot import select_pilot_target

    pilot_target = select_pilot_target(config, args.target)
    needed_vendors = {config.attacker.vendor, pilot_target.vendor}
    missing = [m for m in missing_key_vendors(config, registry)
               if any(m.startswith(v.value) for v in needed_vendors)]
    if missing and not args.allow_missing_keys:
        print(f"ERROR: pilot needs live endpoints; missing keys for: {', '.join(missing)}",
              file=sys.stderr)
        return 2

    out_dir = args.output_dir or str(Path(config.output.dir) / "pilot")
    report = run_pilot(config, models_registry=registry, n=args.n,
                       target=pilot_target, output_dir=out_dir)
    print(report.format())
    return 0


def analyze_cli(argv: list[str] | None = None) -> int:
    parser = _base_parser("Analyze rounds.csv -> KM survival + ASR heatmap")
    parser.add_argument("--rounds-csv", default=None, help="path to rounds.csv")
    parser.add_argument("--out", default=None, help="analysis output directory")
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)
    config, _ = _load(args.config, args.models)

    rounds_csv = Path(args.rounds_csv or Path(config.output.dir) / "rounds.csv")
    if not rounds_csv.exists():
        print(f"ERROR: rounds file not found: {rounds_csv}", file=sys.stderr)
        return 2

    from .analysis.report import analyze_and_report

    out_dir = Path(args.out or Path(config.output.dir) / "analysis")
    summary = analyze_and_report(rounds_csv, out_dir, config=config)
    print(summary)
    return 0


def _base_parser(description: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--config", default=None, help="path to experiment.yaml")
    p.add_argument("--models", default=None, help="path to models.yaml")
    p.add_argument("--output-dir", default=None, help="override output dir")
    p.add_argument("--allow-missing-keys", action="store_true",
                   help="proceed even if some vendor keys are absent")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run_experiment_cli())
