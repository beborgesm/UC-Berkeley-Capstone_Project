#!/usr/bin/env python
"""Run the required PILOT GATE (N=3 on one confidentiality + one integrity cell
against real endpoints) before scaling to the full grid.

    python scripts/pilot.py            # uses config/experiment.yaml
    python scripts/pilot.py -n 5 -v
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from breachbench.cli import pilot_cli  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(pilot_cli())
