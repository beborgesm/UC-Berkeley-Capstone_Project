"""Per-run JSONL transcript store (audit + future human gold-set labeling).

Full prompts/responses live here so the CSV can stay lean via `transcript_ref`.
One JSON object per round, appended to runs/<run_id>.jsonl.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..loop.types import RoundResult, RunResult


def _round_record(result: "RunResult", rr: "RoundResult") -> dict[str, Any]:
    tr = rr.target_response
    canary = None
    if rr.canary_result is not None:
        cr = rr.canary_result
        canary = {
            "matched": cr.matched,
            "method": cr.method,
            "transform_name": cr.transform_name,
            "partial_match": cr.partial_match,
            "partial_run_len": cr.partial_run_len,
        }
    tool = None
    if rr.dispatch_result is not None:
        dr = rr.dispatch_result
        tool = {"fired": dr.fired, "detection": dr.detection, "arguments": dr.arguments}
    return {
        "run_id": result.run_id,
        "round_index": rr.round_index,
        "transcript_ref": f"{result.run_id}#{rr.round_index}",
        "timestamp_utc": rr.timestamp_utc,
        "attacker_prompt": rr.attacker_prompt,
        "target_text": tr.text,
        "target_tool_calls": [
            {"name": c.name, "arguments": c.arguments, "source": c.source}
            for c in tr.tool_calls
        ],
        "detection": {"canary": canary, "tool": tool},
        "breach_this_round": rr.breach_this_round,
        "target_resolved_model_version": tr.resolved_model_version,
        "api_status": tr.http_status,
        "error": tr.error,
        "timing_ms": {
            "attacker": rr.attacker_response.latency_ms,
            "target": tr.latency_ms,
        },
        "judge": _judge_record(rr.judge_result),
    }


def _judge_record(jr: Any) -> dict[str, Any] | None:
    if jr is None:
        return None
    return {
        "verdict": getattr(jr, "verdict", None),
        "degradation_score": getattr(jr, "degradation_score", None),
        "rationale": getattr(jr, "rationale", None),
        "authoritative": bool(getattr(jr, "authoritative", False)),
    }


class TranscriptStore:
    def __init__(self, directory: str | Path) -> None:
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, run_id: str) -> Path:
        return self.dir / f"{run_id}.jsonl"

    def write_run(self, result: "RunResult") -> Path:
        """Write all rounds of a run to its JSONL file (overwrites — one file per
        run, keyed by the deterministic run_id, so a re-run is idempotent)."""
        path = self.path_for(result.run_id)
        with path.open("w", encoding="utf-8") as fh:
            for rr in result.rounds:
                fh.write(json.dumps(_round_record(result, rr), default=str) + "\n")
        return path
