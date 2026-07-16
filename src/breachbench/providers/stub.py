"""StubProvider: a deterministic, offline ChatProvider for tests and dry runs.

It never touches the network. A `responder` callable turns each call's context
into a scripted ChatResponse, so tests can drive an Attacker that escalates and a
Target that leaks the canary or fires the forbidden tool at a chosen round —
exercising the full loop, detection, and recording paths with zero API cost.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from ..config.schema import RetryConfig
from .base import AbstractProvider
from .types import ChatResponse, Message, ToolChoice, ToolSpec


@dataclass
class StubCallContext:
    call_index: int  # 1-based count of calls made to THIS provider instance
    messages: Sequence[Message]
    tools: Sequence[ToolSpec] | None
    tool_choice: ToolChoice
    temperature: float
    seed: int | None
    model_version: str


Responder = Callable[[StubCallContext], ChatResponse]


class StubProvider(AbstractProvider):
    vendor = "stub"

    def __init__(
        self,
        responder: Responder,
        *,
        supports_native_tools: bool = True,
        supports_seed: bool = True,
    ) -> None:
        # No retries/backoff by default so tests that simulate operational errors
        # fail fast without real sleeps.
        super().__init__(retry=RetryConfig(max_attempts=1, initial_backoff_s=0.001, max_backoff_s=0.001))
        self._responder = responder
        self.supports_native_tools = supports_native_tools
        self.supports_seed = supports_seed
        self._calls = 0

    def _build_client(self) -> Any:  # no client needed
        return object()

    def _raw_chat(
        self,
        *,
        model_version: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec] | None,
        tool_choice: ToolChoice,
        temperature: float,
        seed: int | None,
        max_tokens: int | None,
        timeout_s: float,
    ) -> ChatResponse:
        self._calls += 1
        ctx = StubCallContext(
            call_index=self._calls,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            seed=seed,
            model_version=model_version,
        )
        resp = self._responder(ctx)
        # Ensure the resolved version is populated even if the responder omitted it.
        if not resp.resolved_model_version:
            resp = ChatResponse(
                text=resp.text,
                tool_calls=resp.tool_calls,
                resolved_model_version=f"stub/{model_version}",
                finish_reason=resp.finish_reason,
                usage=resp.usage,
                latency_ms=resp.latency_ms,
                http_status=resp.http_status,
                retries=resp.retries,
                error=resp.error,
                raw=resp.raw,
            )
        return resp


# ---- convenience responder builders for tests --------------------------------
def text_responder(text: str) -> Responder:
    """Always returns the same text (handy for a trivial Attacker)."""

    def _r(ctx: StubCallContext) -> ChatResponse:
        return ChatResponse(
            text=text,
            tool_calls=[],
            resolved_model_version=f"stub/{ctx.model_version}",
            finish_reason="stop",
            http_status=200,
        )

    return _r
