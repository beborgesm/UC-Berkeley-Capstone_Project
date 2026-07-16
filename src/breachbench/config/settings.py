"""Lazy environment/secret resolution.

Nothing here reads a key at import time. `resolve_api_key` is called only when an
adapter is about to make its first request. `.env` is loaded (if present) on first
resolution, not on import, so the package imports cleanly with no keys and no file.
"""

from __future__ import annotations

import os
import threading

_DOTENV_LOADED = False
_LOCK = threading.Lock()


def _ensure_dotenv_loaded() -> None:
    """Load `.env` once, on first key resolution. Safe if python-dotenv or the
    file is absent."""
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    with _LOCK:
        if _DOTENV_LOADED:
            return
        try:
            from dotenv import load_dotenv

            load_dotenv(override=False)
        except Exception:
            # Absent dotenv or unreadable file must never break import/usage.
            pass
        _DOTENV_LOADED = True


class MissingAPIKeyError(RuntimeError):
    """Raised only at call time when a required key is absent — never at import."""


def resolve_api_key(env_var: str, *, required: bool = True) -> str | None:
    """Resolve an API key from the environment, loading `.env` lazily first."""
    _ensure_dotenv_loaded()
    value = os.environ.get(env_var)
    if value:
        return value
    if required:
        raise MissingAPIKeyError(
            f"Environment variable '{env_var}' is not set. Populate it (see .env.example) "
            f"before making live API calls."
        )
    return None


def has_api_key(env_var: str) -> bool:
    """Non-raising probe used by the pilot/runner to skip cells with no credentials."""
    _ensure_dotenv_loaded()
    return bool(os.environ.get(env_var))
