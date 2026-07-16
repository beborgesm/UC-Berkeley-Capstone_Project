"""Provider-agnostic message / tool / response types.

These are the ONLY types the core loop knows about. Each vendor adapter maps its
native request/response into these frozen dataclasses, so the loop, detection, and
recording layers never import a vendor SDK.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Sequence

Role = Literal["system", "user", "assistant", "tool"]
ToolChoice = Literal["auto", "none", "required"]
ToolCallSource = Literal["native", "text_protocol"]


@dataclass(frozen=True)
class Message:
    role: Role
    content: str
    tool_call_id: str | None = None  # for role="tool" replies (mock tool result)
    name: str | None = None


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    source: ToolCallSource
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@dataclass(frozen=True)
class ChatResponse:
    """Normalized result of a single chat-completion call, with full telemetry.

    `error`/`http_status`/`retries` are populated even on failure so a round that
    hit a rate limit or timeout stays fully inspectable rather than vanishing.
    """

    text: str
    tool_calls: list[ToolCall]
    resolved_model_version: str  # EXACT string the vendor reports/used — logged every call
    finish_reason: str | None = None  # "length" maps to a truncation flag downstream
    usage: Usage | None = None
    latency_ms: float = 0.0
    http_status: int | None = None
    retries: int = 0
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def truncated(self) -> bool:
        return self.finish_reason == "length"

    @property
    def ok(self) -> bool:
        return self.error is None


def system(content: str) -> Message:
    return Message(role="system", content=content)


def user(content: str) -> Message:
    return Message(role="user", content=content)


def assistant(content: str) -> Message:
    return Message(role="assistant", content=content)


def flatten_history(history: Sequence[tuple[str, str]]) -> list[Message]:
    """Turn [(attacker_prompt, target_text), ...] into alternating user/assistant
    messages for the growing within-run Target conversation."""
    out: list[Message] = []
    for attacker_prompt, target_text in history:
        out.append(user(attacker_prompt))
        out.append(assistant(target_text))
    return out
