"""Groq (Llama) adapter via the `groq` SDK (OpenAI-compatible chat API).

Lazy client + key. Groq ignores `seed` for reproducibility purposes
(supports_seed defaults False). Some Groq-hosted models lack native tool-calling;
for those, `supports_native_tools=False` is set from models.yaml and the integrity
scenario uses the text-protocol fallback (no `tools` are sent).

Not exercised by the offline test suite (needs a live key).
"""

from __future__ import annotations

import json
from typing import Any, Sequence

from ..config.schema import RetryConfig
from ..config.settings import resolve_api_key
from .base import AbstractProvider
from .retry import ErrorType, ProviderError, classify_http_status, extract_retry_after
from .types import ChatResponse, Message, ToolCall, ToolChoice, ToolSpec, Usage


class GroqAdapter(AbstractProvider):
    vendor = "groq"

    def __init__(
        self,
        *,
        api_key_env: str = "GROQ_API_KEY",
        retry: RetryConfig | None = None,
        supports_native_tools: bool = True,
        supports_seed: bool = False,
    ) -> None:
        super().__init__(retry=retry)
        self._api_key_env = api_key_env
        self.supports_native_tools = supports_native_tools
        self.supports_seed = supports_seed

    def _build_client(self) -> Any:
        try:
            from groq import Groq
        except ImportError as exc:  # pragma: no cover
            raise ProviderError(
                ErrorType.OTHER,
                "groq SDK not installed; `pip install groq` (extras [groq]).",
            ) from exc
        return Groq(api_key=resolve_api_key(self._api_key_env))

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
        kwargs: dict[str, Any] = {
            "model": model_version,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        # Only send native tools if this model supports them.
        if tools and self.supports_native_tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]
            kwargs["tool_choice"] = tool_choice

        try:
            completion = self._client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            raise _normalize_exception(exc) from exc

        return _from_groq_completion(completion, model_version)


def _from_groq_completion(completion: Any, model_version: str) -> ChatResponse:
    choice = completion.choices[0]
    message = choice.message
    text = getattr(message, "content", None) or ""
    tool_calls: list[ToolCall] = []
    for tc in getattr(message, "tool_calls", None) or []:
        try:
            args = json.loads(tc.function.arguments or "{}")
        except (json.JSONDecodeError, TypeError):
            args = {"_raw_arguments": getattr(tc.function, "arguments", None)}
        tool_calls.append(
            ToolCall(id=tc.id, name=tc.function.name, arguments=args, source="native")
        )
    usage = None
    if getattr(completion, "usage", None) is not None:
        usage = Usage(
            prompt_tokens=getattr(completion.usage, "prompt_tokens", None),
            completion_tokens=getattr(completion.usage, "completion_tokens", None),
        )
    return ChatResponse(
        text=text,
        tool_calls=tool_calls,
        resolved_model_version=getattr(completion, "model", model_version),
        finish_reason=getattr(choice, "finish_reason", None),
        usage=usage,
        http_status=200,
    )


def _normalize_exception(exc: Exception) -> ProviderError:
    status = getattr(exc, "status_code", None)
    name = type(exc).__name__
    if "RateLimit" in name or status == 429:
        return ProviderError(ErrorType.RATE_LIMIT, str(exc), http_status=status or 429,
                             retryable=True, retry_after=extract_retry_after(exc))
    if "Timeout" in name or status == 408:
        return ProviderError(ErrorType.TIMEOUT, str(exc), http_status=status, retryable=True)
    if "Connection" in name or "Network" in name:
        return ProviderError(ErrorType.CONNECTION, str(exc), http_status=None, retryable=True)
    if status is not None:
        etype, retryable = classify_http_status(status)
        return ProviderError(etype, str(exc), http_status=status, retryable=retryable)
    return ProviderError(ErrorType.OTHER, f"{name}: {exc}", retryable=False)
