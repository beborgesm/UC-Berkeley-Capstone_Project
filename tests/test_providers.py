"""Adapter error-classification tests (no network — just the mapping logic).

Regression guard for the overnight incident where transient APIConnectionErrors
(wifi dropping on sleep) were classified non-retryable and instantly invalidated runs.
"""

from __future__ import annotations

from breachbench.providers.retry import ErrorType


class APIConnectionError(Exception):
    """Mimics the openai/groq SDK connection error (name is what we match on)."""


class RateLimitError(Exception):
    status_code = 429


class APITimeoutError(Exception):
    pass


def test_openai_connection_error_is_retryable():
    from breachbench.providers.openai_adapter import _normalize_exception

    err = _normalize_exception(APIConnectionError("Connection error."))
    assert err.retryable is True
    assert err.error_type == ErrorType.CONNECTION


def test_openai_rate_limit_and_timeout_retryable():
    from breachbench.providers.openai_adapter import _normalize_exception

    assert _normalize_exception(RateLimitError("429")).retryable is True
    assert _normalize_exception(APITimeoutError("timed out")).retryable is True


def test_groq_and_gemini_connection_errors_retryable():
    from breachbench.providers.groq_adapter import _normalize_exception as groq_norm
    from breachbench.providers.gemini_adapter import _normalize_exception as gem_norm

    assert groq_norm(APIConnectionError("Connection error.")).retryable is True
    assert gem_norm(APIConnectionError("Connection error.")).retryable is True


def test_unknown_error_stays_non_retryable():
    from breachbench.providers.openai_adapter import _normalize_exception

    err = _normalize_exception(ValueError("bad request, malformed"))
    assert err.retryable is False
