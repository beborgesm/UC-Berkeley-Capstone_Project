"""ChatProvider protocol + AbstractProvider base (lazy client, retry, telemetry).

An adapter subclasses AbstractProvider and implements exactly one method,
`_raw_chat`, which performs a single low-level call and returns a ChatResponse or
raises ProviderError. The base wraps it in retry/backoff, times it, and guarantees
`resolved_model_version`, `latency_ms`, `retries`, `http_status`, and `error` are
always populated.

The underlying SDK client is constructed lazily on first use (`_client`), never at
import — so `import breachbench` with no keys is safe.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Protocol, Sequence, runtime_checkable

from ..config.schema import RetryConfig
from .retry import ProviderError, execute_with_retry
from .types import ChatResponse, Message, ToolChoice, ToolSpec


@runtime_checkable
class ChatProvider(Protocol):
    vendor: str
    supports_native_tools: bool
    supports_seed: bool

    def chat(
        self,
        *,
        model_version: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec] | None = None,
        tool_choice: ToolChoice = "auto",
        temperature: float,
        seed: int | None = None,
        max_tokens: int | None = None,
        timeout_s: float = 60.0,
    ) -> ChatResponse: ...


class AbstractProvider(ABC):
    """Shared adapter machinery. Subclasses implement `_raw_chat` and `_build_client`."""

    vendor: str = "abstract"
    supports_native_tools: bool = True
    supports_seed: bool = False

    def __init__(self, *, retry: RetryConfig | None = None) -> None:
        self._retry = retry or RetryConfig()
        self.__client: Any = None  # lazy; constructed on first chat()

    # ---- lazy client -----------------------------------------------------
    @property
    def _client(self) -> Any:
        if self.__client is None:
            self.__client = self._build_client()
        return self.__client

    @abstractmethod
    def _build_client(self) -> Any:
        """Construct and return the vendor SDK client. Called lazily, may resolve
        the API key here (never at import)."""

    @abstractmethod
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
        """One low-level call. Return a ChatResponse or raise ProviderError."""

    # ---- public API ------------------------------------------------------
    def chat(
        self,
        *,
        model_version: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec] | None = None,
        tool_choice: ToolChoice = "auto",
        temperature: float,
        seed: int | None = None,
        max_tokens: int | None = None,
        timeout_s: float = 60.0,
    ) -> ChatResponse:
        start = time.perf_counter()

        def _call() -> ChatResponse:
            return self._raw_chat(
                model_version=model_version,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                temperature=temperature,
                seed=seed if self.supports_seed else None,
                max_tokens=max_tokens,
                timeout_s=timeout_s,
            )

        result, outcome = execute_with_retry(
            _call,
            max_attempts=self._retry.max_attempts,
            initial_backoff_s=self._retry.initial_backoff_s,
            max_backoff_s=self._retry.max_backoff_s,
        )
        latency_ms = (time.perf_counter() - start) * 1000.0

        if result is None:
            # Terminal failure: synthesize an errored, fully-inspectable response.
            return ChatResponse(
                text="",
                tool_calls=[],
                resolved_model_version=model_version,
                finish_reason=None,
                usage=None,
                latency_ms=latency_ms,
                http_status=outcome.http_status,
                retries=outcome.retries,
                error=f"{outcome.error_type}: {outcome.error_message}",
                raw={"error_type": outcome.error_type},
            )

        # Success: stamp measured latency and retry count onto the response.
        return ChatResponse(
            text=result.text,
            tool_calls=result.tool_calls,
            resolved_model_version=result.resolved_model_version or model_version,
            finish_reason=result.finish_reason,
            usage=result.usage,
            latency_ms=latency_ms,
            http_status=result.http_status if result.http_status is not None else 200,
            retries=outcome.retries,
            error=None,
            raw=result.raw,
        )


__all__ = ["AbstractProvider", "ChatProvider", "ProviderError"]
