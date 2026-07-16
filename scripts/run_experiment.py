#!/usr/bin/env python
"""Run the full BreachBenchmark experiment grid (resumable).

    python scripts/run_experiment.py            # uses config/experiment.yaml
    python scripts/run_experiment.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from breachbench.cli import run_experiment_cli  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(run_experiment_cli())
