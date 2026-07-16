"""OpenAI chat-completions adapter.

The `openai` SDK and the API key are resolved lazily inside `_build_client`, so
importing this module with the package requires neither the SDK nor a key.
"""

from __future__ import annotations

import json
from typing import Any, Sequence

from ..config.schema import RetryConfig
from ..config.settings import resolve_api_key
from .base import AbstractProvider
from .retry import ErrorType, ProviderError, classify_http_status, extract_retry_after
from .types import ChatResponse, Message, ToolCall, ToolChoice, ToolSpec, Usage


class OpenAIAdapter(AbstractProvider):
    vendor = "openai"
    supports_native_tools = True
    supports_seed = True

    def __init__(
        self,
        *,
        api_key_env: str = "OPENAI_API_KEY",
        retry: RetryConfig | None = None,
        supports_native_tools: bool = True,
        supports_seed: bool = True,
    ) -> None:
        super().__init__(retry=retry)
        self._api_key_env = api_key_env
        self.supports_native_tools = supports_native_tools
        self.supports_seed = supports_seed

    def _build_client(self) -> Any:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - environment-dependent
            raise ProviderError(
                error_type=ErrorType.OTHER,
                message="openai SDK not installed; `pip install openai` (or extras [openai]).",
            ) from exc
        api_key = resolve_api_key(self._api_key_env)
        return OpenAI(api_key=api_key)

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
        payload_messages = [_to_openai_message(m) for m in messages]
        kwargs: dict[str, Any] = {
            "model": model_version,
            "messages": payload_messages,
            "temperature": temperature,
            "timeout": timeout_s,
        }
        if seed is not None:
            kwargs["seed"] = seed
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if tools:
            kwargs["tools"] = [_to_openai_tool(t) for t in tools]
            kwargs["tool_choice"] = tool_choice

        try:
            completion = self._client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 - normalize SDK exceptions
            raise _normalize_exception(exc) from exc

        return _from_openai_completion(completion, model_version)


def _to_openai_message(m: Message) -> dict[str, Any]:
    msg: dict[str, Any] = {"role": m.role, "content": m.content}
    if m.tool_call_id:
        msg["tool_call_id"] = m.tool_call_id
    if m.name:
        msg["name"] = m.name
    return msg


def _to_openai_tool(t: ToolSpec) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": t.name,
            "description": t.description,
            "parameters": t.parameters,
        },
    }


def _from_openai_completion(completion: Any, model_version: str) -> ChatResponse:
    choice = completion.choices[0]
    message = choice.message
    text = message.content or ""
    tool_calls: list[ToolCall] = []
    for tc in getattr(message, "tool_calls", None) or []:
        try:
            args = json.loads(tc.function.arguments or "{}")
        except (json.JSONDecodeError, TypeError):
            args = {"_raw_arguments": getattr(tc.function, "arguments", None)}
        tool_calls.append(
            ToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=args,
                source="native",
                raw={"id": tc.id, "name": tc.function.name},
            )
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
        raw={"id": getattr(completion, "id", None)},
    )


def _normalize_exception(exc: Exception) -> ProviderError:
    """Map an openai SDK exception to a classified, retry-aware ProviderError."""
    status = getattr(exc, "status_code", None)
    name = type(exc).__name__
    if "RateLimit" in name or status == 429:
        return ProviderError(ErrorType.RATE_LIMIT, str(exc), http_status=status or 429,
                             retryable=True, retry_after=extract_retry_after(exc))
    if "Timeout" in name or status == 408:
        return ProviderError(ErrorType.TIMEOUT, str(exc), http_status=status, retryable=True)
    # Transient network drops (APIConnectionError, DNS, wifi flap on sleep/wake) MUST retry,
    # not instantly invalidate the run.
    if "Connection" in name or "Network" in name:
        return ProviderError(ErrorType.CONNECTION, str(exc), http_status=None, retryable=True)
    if status is not None:
        etype, retryable = classify_http_status(status)
        return ProviderError(etype, str(exc), http_status=status, retryable=retryable)
    return ProviderError(ErrorType.OTHER, f"{name}: {exc}", retryable=False)
