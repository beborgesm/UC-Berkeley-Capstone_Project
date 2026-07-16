"""Append-only, schema-enforced rounds.csv writer.

The header is written once on file creation; every row is validated against the
authoritative COLUMNS order. Appends are flushed immediately so a crash mid-grid
leaves a complete, resumable file (the runner ledger keys off run_id).
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any, Iterable

from .schema import COLUMNS


class RoundsCsvWriter:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._existed = self.path.exists() and self.path.stat().st_size > 0

    def _ensure_header(self, fh) -> None:
        if not self._existed:
            writer = csv.DictWriter(fh, fieldnames=list(COLUMNS), extrasaction="raise")
            writer.writeheader()
            self._existed = True

    def append_rows(self, rows: Iterable[dict[str, Any]]) -> int:
        rows = list(rows)
        if not rows:
            return 0
        with self.path.open("a", newline="", encoding="utf-8") as fh:
            self._ensure_header(fh)
            writer = csv.DictWriter(fh, fieldnames=list(COLUMNS), extrasaction="raise")
            for row in rows:
                missing = set(COLUMNS) - set(row)
                if missing:
                    raise ValueError(f"row missing required columns: {sorted(missing)}")
                writer.writerow({k: row[k] for k in COLUMNS})
            fh.flush()
            os.fsync(fh.fileno())
        return len(rows)
