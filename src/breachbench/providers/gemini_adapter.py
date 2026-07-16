"""Google Gemini (Flash) adapter via the `google-genai` SDK.

Lazy client + key. Gemini generally ignores `seed` (supports_seed defaults False),
so reproducibility is best-effort only. When a target lacks native tools the loop
falls back to the text-protocol; this adapter still maps native function-calls when
present.

Not exercised by the offline test suite (needs a live key); structurally mirrors
the OpenAI adapter's normalization so the loop sees identical ChatResponse shapes.
"""

from __future__ import annotations

from typing import Any, Sequence

from ..config.schema import RetryConfig
from ..config.settings import resolve_api_key
from .base import AbstractProvider
from .retry import ErrorType, ProviderError, extract_retry_after
from .types import ChatResponse, Message, ToolCall, ToolChoice, ToolSpec, Usage


class GeminiAdapter(AbstractProvider):
    vendor = "gemini"

    def __init__(
        self,
        *,
        api_key_env: str = "GEMINI_API_KEY",
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
            from google import genai
        except ImportError as exc:  # pragma: no cover
            raise ProviderError(
                ErrorType.OTHER,
                "google-genai SDK not installed; `pip install google-genai` (extras [gemini]).",
            ) from exc
        return genai.Client(api_key=resolve_api_key(self._api_key_env))

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
        from google.genai import types  # local import (lazy)

        system_instruction, contents = _split_messages(messages)
        cfg_kwargs: dict[str, Any] = {"temperature": temperature}
        if system_instruction:
            cfg_kwargs["system_instruction"] = system_instruction
        if max_tokens is not None:
            cfg_kwargs["max_output_tokens"] = max_tokens
        if tools:
            cfg_kwargs["tools"] = [
                types.Tool(function_declarations=[
                    types.FunctionDeclaration(
                        name=t.name, description=t.description, parameters=t.parameters
                    )
                    for t in tools
                ])
            ]

        try:
            resp = self._client.models.generate_content(
                model=model_version,
                contents=contents,
                config=types.GenerateContentConfig(**cfg_kwargs),
            )
        except Exception as exc:  # noqa: BLE001
            raise _normalize_exception(exc) from exc

        return _from_gemini_response(resp, model_version)


def _split_messages(messages: Sequence[Message]) -> tuple[str, list[dict[str, Any]]]:
    """Extract the system instruction and map the rest to Gemini contents
    (roles: user / model)."""
    system_parts: list[str] = []
    contents: list[dict[str, Any]] = []
    for m in messages:
        if m.role == "system":
            system_parts.append(m.content)
        elif m.role == "assistant":
            contents.append({"role": "model", "parts": [{"text": m.content}]})
        else:  # user / tool
            contents.append({"role": "user", "parts": [{"text": m.content}]})
    return "\n\n".join(system_parts), contents


def _from_gemini_response(resp: Any, model_version: str) -> ChatResponse:
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    finish_reason = None
    candidates = getattr(resp, "candidates", None) or []
    if candidates:
        cand = candidates[0]
        finish_reason = str(getattr(cand, "finish_reason", "") or "") or None
        content = getattr(cand, "content", None)
        for part in getattr(content, "parts", None) or []:
            fc = getattr(part, "function_call", None)
            if fc is not None:
                tool_calls.append(
                    ToolCall(
                        id=getattr(fc, "id", "") or f"gemini_{fc.name}",
                        name=fc.name,
                        arguments=dict(getattr(fc, "args", {}) or {}),
                        source="native",
                        raw={"name": fc.name},
                    )
                )
            elif getattr(part, "text", None):
                text_parts.append(part.text)

    usage = None
    um = getattr(resp, "usage_metadata", None)
    if um is not None:
        usage = Usage(
            prompt_tokens=getattr(um, "prompt_token_count", None),
            completion_tokens=getattr(um, "candidates_token_count", None),
        )

    return ChatResponse(
        text="".join(text_parts),
        tool_calls=tool_calls,
        resolved_model_version=getattr(resp, "model_version", None) or model_version,
        finish_reason=finish_reason,
        usage=usage,
        http_status=200,
        raw={},
    )


def _normalize_exception(exc: Exception) -> ProviderError:
    name = type(exc).__name__
    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if "ResourceExhausted" in name or status == 429:
        return ProviderError(ErrorType.RATE_LIMIT, str(exc), http_status=429, retryable=True,
                             retry_after=extract_retry_after(exc))
    if "DeadlineExceeded" in name or "Timeout" in name:
        return ProviderError(ErrorType.TIMEOUT, str(exc), http_status=status, retryable=True)
    if "Connection" in name or "Network" in name:
        return ProviderError(ErrorType.CONNECTION, str(exc), http_status=None, retryable=True)
    if "ServiceUnavailable" in name or "Internal" in name or (isinstance(status, int) and status >= 500):
        return ProviderError(ErrorType.OTHER, str(exc), http_status=status, retryable=True)
    return ProviderError(ErrorType.OTHER, f"{name}: {exc}", http_status=status, retryable=False)
