"""Deterministic breach detection (PRIMARY): canary matching + tool-fire capture.

These signals decide confidentiality and integrity breaches in code, independent of
the Judge.
"""

from .canary_match import MatchMethod, MatchResult, match_canary
from .tool_dispatch import DetectionMethod, DispatchResult, MockToolDispatcher
from .transforms import TRANSFORM_NAMES, TRANSFORMS

__all__ = [
    "DetectionMethod",
    "DispatchResult",
    "MatchMethod",
    "MatchResult",
    "MockToolDispatcher",
    "TRANSFORMS",
    "TRANSFORM_NAMES",
    "match_canary",
]
