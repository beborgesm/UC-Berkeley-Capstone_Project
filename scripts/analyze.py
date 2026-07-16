#!/usr/bin/env python
"""Analyze a completed rounds.csv: Kaplan–Meier survival, ASR@k_max heatmap, and
optional pre-registered log-rank tests.

    python scripts/analyze.py --rounds-csv output/rounds.csv --out output/analysis
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from breachbench.cli import analyze_cli  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(analyze_cli())
