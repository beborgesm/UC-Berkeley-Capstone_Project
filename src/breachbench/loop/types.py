"""Loop data contracts: the experimental cell, per-round and per-run results, and
deterministic seed derivation.

A RunResult is one Kaplan–Meier survival trial. The run-level fields
(duration_rounds, event_observed, censored, termination_reason, run_valid) are the
exact KM encoding; the recording layer projects them with no reshaping.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum

from ..config.schema import AttackVector, ModelSpec
from ..detection.canary_match import MatchResult
from ..detection.tool_dispatch import DispatchResult
from ..providers.types import ChatResponse

_SEED_MODULUS = 2**31 - 1


class TerminationReason(str, Enum):
    BREACH_CONFIDENTIALITY = "BREACH_CONFIDENTIALITY"
    BREACH_INTEGRITY = "BREACH_INTEGRITY"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    ADMIN_CENSORED_ERROR = "ADMIN_CENSORED_ERROR"
    INVALIDATED = "INVALIDATED"


@dataclass(frozen=True)
class Cell:
    """One grid coordinate: (target model × scenario × attack vector).

    The Attacker is a fixed instrument and is NOT part of the cell key.
    """

    target: ModelSpec
    scenario_id: str
    attack_vector: AttackVector

    def cell_id(self) -> str:
        key = f"{self.target.label()}|{self.scenario_id}|{self.attack_vector.value}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]


def _stable_int(*parts: object) -> int:
    key = "|".join(str(p) for p in parts)
    digest = hashlib.sha256(key.encode()).digest()
    return int.from_bytes(digest[:8], "big")


def derive_run_seed(master_seed: int, cell_id: str, repetition_index: int) -> int:
    """Deterministic per-run seed. Fully determines canary + attacker sampling
    inputs; structure is reproducible even though live responses are not."""
    return _stable_int(master_seed, cell_id, repetition_index) % _SEED_MODULUS


def derive_canary_seed(run_seed: int) -> int:
    return _stable_int("canary", run_seed) % _SEED_MODULUS


@dataclass
class RoundResult:
    round_index: int  # k, 1-based
    attacker_prompt: str
    attacker_response: ChatResponse
    target_response: ChatResponse
    breach_this_round: bool
    canary_result: MatchResult | None = None
    dispatch_result: DispatchResult | None = None
    judge_result: object | None = None  # JudgeResult when the Judge is enabled (secondary)
    error_type: str = "NONE"
    error_flag: bool = False
    timestamp_utc: str = ""

    @property
    def valid(self) -> bool:
        """A round is valid iff the Target call succeeded (no operational error)."""
        return self.target_response.ok


@dataclass
class RunResult:
    run_id: str
    cell: Cell
    repetition_index: int
    run_seed: int
    canary_seed: int
    canary: str | None  # the actual token (meaningless), stored for audit
    attacker_model_version: str
    rounds: list[RoundResult] = field(default_factory=list)

    # Run-level survival encoding (the KM contract):
    duration_rounds: int = 0
    event_observed: int = 0  # 1 iff the run ended in a breach
    censored: int = 0  # 1 iff right-censored (survived) or administratively censored
    termination_reason: TerminationReason = TerminationReason.BUDGET_EXHAUSTED
    run_valid: int = 1

    @property
    def breached(self) -> bool:
        return self.event_observed == 1
