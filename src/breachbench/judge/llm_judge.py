"""Single LLM judge (SECONDARY). Brand-blind, isolation-safe, canary-free.

Its verdict is recorded but can NEVER flip a deterministic breach — the loop treats
the result as advisory only.
"""

from __future__ import annotations

import json
import re

from ..providers.base import ChatProvider
from .prompts import build_judge_messages
from .schema import DEGRADATION_MAX, DEGRADATION_MIN, JudgeResult, JudgeVerdict

_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


class LLMJudge:
    def __init__(
        self,
        *,
        provider: ChatProvider,
        model_version: str,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> None:
        self._provider = provider
        self._model_version = model_version
        self._temperature = temperature
        self._seed = seed

    @property
    def model_version(self) -> str:
        return self._model_version

    def evaluate(self, *, target_output: str, scenario_class: str) -> JudgeResult:
        messages = build_judge_messages(target_output, scenario_class)
        resp = self._provider.chat(
            model_version=self._model_version,
            messages=messages,
            tools=None,
            tool_choice="none",
            temperature=self._temperature,
            seed=self._seed,
        )
        return parse_judge_output(resp.text)


def parse_judge_output(text: str) -> JudgeResult:
    payload = _extract_json(text)
    if payload is None:
        return JudgeResult(
            verdict=JudgeVerdict.NO_DEGRADATION,
            degradation_score=0,
            rationale="unparseable judge output",
            parse_error=True,
        )
    verdict = _coerce_verdict(payload.get("verdict"))
    score = _coerce_score(payload.get("degradation_score"))
    rationale = str(payload.get("rationale", ""))[:500]
    return JudgeResult(verdict=verdict, degradation_score=score, rationale=rationale)


def _extract_json(text: str) -> dict | None:
    if not text:
        return None
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    match = _JSON_OBJ_RE.search(text)
    if match:
        try:
            obj = json.loads(match.group(0))
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _coerce_verdict(value: object) -> JudgeVerdict:
    try:
        return JudgeVerdict(str(value))
    except ValueError:
        return JudgeVerdict.NO_DEGRADATION


def _coerce_score(value: object) -> int:
    try:
        score = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0
    return max(DEGRADATION_MIN, min(DEGRADATION_MAX, score))
