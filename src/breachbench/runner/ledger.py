"""Append-only JSONL ledger for resumability.

Each completed run appends one line; on load the ledger replays them into a set of
completed run_ids. A run is skipped iff its (deterministic) run_id is already
complete. Invalidated runs (run_valid=0) are intentionally NOT marked complete, so
they are rescheduled on the next invocation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Ledger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._completed: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("type") == "complete" and "run_id" in rec:
                    self._completed.add(rec["run_id"])

    def is_complete(self, run_id: str) -> bool:
        return run_id in self._completed

    def reconcile_with_rounds(self, rounds_csv: str | Path) -> int:
        """Treat any run that already has a terminal row in rounds.csv as complete,
        even if the ledger never recorded it. This closes the tiny power-off window
        between writing a run's rows and marking it done, so a resumed run never
        re-runs (and thus never duplicates) an already-written run. Returns the
        number of runs recovered from the CSV."""
        p = Path(rounds_csv)
        if not p.exists() or p.stat().st_size == 0:
            return 0
        import csv as _csv

        recovered = 0
        with p.open("r", newline="", encoding="utf-8") as fh:
            for row in _csv.DictReader(fh):
                if row.get("is_terminal_round") in ("1", 1) and row.get("run_id"):
                    rid = row["run_id"]
                    if rid not in self._completed:
                        self._completed.add(rid)
                        self._append({"type": "complete", "run_id": rid, "source": "csv_reconcile"})
                        recovered += 1
        return recovered

    def _append(self, record: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str) + "\n")
            fh.flush()

    def mark_complete(self, run_id: str, meta: dict[str, Any] | None = None) -> None:
        if run_id in self._completed:
            return
        self._completed.add(run_id)
        self._append({"type": "complete", "run_id": run_id, **(meta or {})})

    def mark_skipped(self, cell_id: str, reason: str, meta: dict[str, Any] | None = None) -> None:
        self._append({"type": "skip", "cell_id": cell_id, "reason": reason, **(meta or {})})

    @property
    def completed_count(self) -> int:
        return len(self._completed)
