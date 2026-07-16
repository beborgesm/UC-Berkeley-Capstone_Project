"""Secondary, non-authoritative LLM Judge: isolation-safe, brand-blind, panel-ready.

The Judge scores only qualitative degradation and can never define a primary breach.
"""

from .base import Judge, JudgePanel
from .llm_judge import LLMJudge, parse_judge_output
from .prompts import build_judge_messages
from .schema import (
    DEGRADATION_MAX,
    DEGRADATION_MIN,
    JudgeResult,
    JudgeVerdict,
)

__all__ = [
    "DEGRADATION_MAX",
    "DEGRADATION_MIN",
    "Judge",
    "JudgePanel",
    "JudgeResult",
    "JudgeVerdict",
    "LLMJudge",
    "build_judge_messages",
    "parse_judge_output",
]
