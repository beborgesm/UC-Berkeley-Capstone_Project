#!/usr/bin/env python
"""Derive the published benchmark dataset from the raw collection.

`data/rounds_raw.csv` holds every run the harness ever completed (523 runs across 4 target
models). The headline analysis runs on the **balanced** subset: only the targets declared in
`config/experiment.yaml`, i.e. the three models with a complete 8-cell grid at full N. This
script is that filter, so the subset is reproducible rather than a hand-made artifact.

The filter matches on the STABLE configured cell identity (`Cell.cell_id()`), never on the
resolved model-version string the endpoint returns — resolved strings drift
(`gpt-4o-mini` -> `gpt-4o-mini-2024-07-18`, `gpt-3.5-turbo` -> `gpt-3.5-turbo-0125`) and a
name-based filter would silently match nothing. This is the same identity rule the log-rank
pairing uses; see analysis/report.py.

    python scripts/make_benchmark_subset.py
    python scripts/make_benchmark_subset.py --in data/rounds_raw.csv --out data/rounds_benchmark.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from breachbench.config.loader import DEFAULT_EXPERIMENT_PATH, load_experiment_config  # noqa: E402
from breachbench.loop.types import Cell  # noqa: E402


def benchmark_cell_ids(config) -> set[str]:
    """Every cell_id the declared roster x scenarios x vectors grid can produce."""
    return {
        Cell(target=t, scenario_id=s, attack_vector=v).cell_id()
        for t in config.targets
        for s in config.scenarios
        for v in config.vectors
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="src", default=str(ROOT / "data" / "rounds_raw.csv"))
    ap.add_argument("--out", dest="dst", default=str(ROOT / "data" / "rounds_benchmark.csv"))
    ap.add_argument("--config", default=DEFAULT_EXPERIMENT_PATH)
    args = ap.parse_args()

    src, dst = Path(args.src), Path(args.dst)
    if not src.exists():
        print(f"ERROR: input not found: {src}", file=sys.stderr)
        return 2

    config = load_experiment_config(args.config)
    keep = benchmark_cell_ids(config)

    df = pd.read_csv(src, low_memory=False)
    subset = df[df["cell_id"].isin(keep)].copy()

    dropped_cells = sorted(set(df["cell_id"]) - keep)
    n_runs = subset["run_id"].nunique()
    n_cells = subset["cell_id"].nunique()

    dst.parent.mkdir(parents=True, exist_ok=True)
    subset.to_csv(dst, index=False)

    roster = ", ".join(t.label() for t in config.targets)
    print(f"roster ({len(config.targets)}): {roster}")
    print(f"grid: {len(config.targets)} targets x {len(config.scenarios)} scenarios "
          f"x {len(config.vectors)} vectors = {len(keep)} cells, N={config.repetitions}")
    print(f"kept   {len(subset):>5} rounds  {n_runs:>4} runs  {n_cells:>3} cells -> {dst}")
    print(f"dropped{len(df) - len(subset):>5} rounds  "
          f"{df['run_id'].nunique() - n_runs:>4} runs  {len(dropped_cells):>3} cells "
          f"(targets outside the declared roster)")
    if n_cells != len(keep):
        print(f"WARNING: {len(keep) - n_cells} declared cell(s) have NO data in {src.name}",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
