"""Retry/backoff classification shared by adapters.

The goal is that free-tier rate limits are *visible* in the data, never silent.
Adapters call `execute_with_retry`, which retries transient failures (429/5xx/
timeout) with exponential backoff + jitter, counts attempts, and classifies the
terminal error so the recording layer can flag throttling artifacts.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

logger = logging.getLogger("breachbench.providers")

T = TypeVar("T")


class ErrorType:
    NONE = "NONE"
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    CONNECTION = "CONNECTION"  # transient network drop (e.g. wifi flap on sleep/wake) — retryable
    TRUNCATION = "TRUNCATION"
    PARSE = "PARSE"
    OTHER = "OTHER"


@dataclass
class ProviderError(Exception):
    """Raised by an adapter's low-level call to signal a classified failure."""

    error_type: str
    message: str
    http_status: int | None = None
    retryable: bool = False
    retry_after: float | None = None  # seconds the server asked us to wait (429 Retry-After)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"[{self.error_type} http={self.http_status}] {self.message}"


# Rate limits reset on the server's schedule (often per-minute), which is far longer
# than a normal exponential backoff — so give them their own patient floor.
_RATE_LIMIT_MIN_BACKOFF_S = 20.0


@dataclass
class RetryOutcome:
    """What `execute_with_retry` observed, regardless of success/failure."""

    retries: int
    http_status: int | None
    error_type: str
    error_message: str | None


def extract_retry_after(exc: Exception) -> float | None:
    """Best-effort read of a 429 Retry-After (seconds) from an SDK exception."""
    resp = getattr(exc, "response", None)
    headers = getattr(resp, "headers", None) if resp is not None else None
    if headers:
        val = headers.get("retry-after") or headers.get("Retry-After")
        if val:
            try:
                return float(val)
            except (ValueError, TypeError):
                pass
    ra = getattr(exc, "retry_after", None)
    try:
        return float(ra) if ra is not None else None
    except (ValueError, TypeError):
        return None


def classify_http_status(status: int | None) -> tuple[str, bool]:
    """Map an HTTP status to (error_type, retryable)."""
    if status is None:
        return ErrorType.OTHER, False
    if status == 429:
        return ErrorType.RATE_LIMIT, True
    if 500 <= status < 600:
        return ErrorType.OTHER, True
    if status == 408:
        return ErrorType.TIMEOUT, True
    return ErrorType.OTHER, False


def execute_with_retry(
    call: Callable[[], T],
    *,
    max_attempts: int,
    initial_backoff_s: float,
    max_backoff_s: float,
    rng: random.Random | None = None,
) -> tuple[T | None, RetryOutcome]:
    """Run `call` with exponential backoff on retryable ProviderErrors.

    Returns `(result_or_None, outcome)`. On terminal failure the result is None and
    the outcome carries the classified error — the caller builds an errored
    ChatResponse from it rather than raising into the loop.
    """
    rng = rng or random.Random()
    attempt = 0
    last_status: int | None = None
    last_error_type = ErrorType.NONE
    last_message: str | None = None

    while attempt < max_attempts:
        try:
            result = call()
            return result, RetryOutcome(attempt, last_status, ErrorType.NONE, None)
        except ProviderError as exc:
            attempt += 1
            last_status = exc.http_status
            last_error_type = exc.error_type
            last_message = exc.message
            if not exc.retryable or attempt >= max_attempts:
                logger.warning(
                    "provider call failed permanently attempt=%d/%d %s",
                    attempt, max_attempts, exc,
                )
                break
            backoff = min(max_backoff_s, initial_backoff_s * (2 ** (attempt - 1)))
            backoff += rng.uniform(0, backoff * 0.25)  # jitter
            if exc.error_type == ErrorType.RATE_LIMIT:
                # Honor the server's Retry-After if given; else wait out the window.
                wanted = exc.retry_after if exc.retry_after else _RATE_LIMIT_MIN_BACKOFF_S
                backoff = min(max_backoff_s, max(backoff, wanted))
            logger.warning(
                "provider call retry attempt=%d/%d backoff=%.2fs %s",
                attempt, max_attempts, backoff, exc,
            )
            time.sleep(backoff)
        except Exception as exc:  # noqa: BLE001 - unknown adapter-level failure
            attempt += 1
            last_error_type = ErrorType.OTHER
            last_message = f"{type(exc).__name__}: {exc}"
            logger.exception("provider call raised unexpectedly")
            break

    return None, RetryOutcome(
        retries=max(0, attempt - 1),
        http_status=last_status,
        error_type=last_error_type,
        error_message=last_message,
    )
