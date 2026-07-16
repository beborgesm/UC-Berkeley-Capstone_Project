"""The package must import and enumerate config with NO keys and NO network.

These tests run with all vendor key env vars stripped to prove lazy init: nothing
resolves a secret or opens a socket at import or config-load time.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _strip_keys(monkeypatch):
    # Also neutralize .env loading so a developer's real .env can't repopulate keys
    # and defeat the point of these "no keys present" tests.
    import breachbench.config.settings as settings

    monkeypatch.setattr(settings, "_DOTENV_LOADED", True)
    for var in ("OPENAI_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    yield


def test_top_level_import_is_clean():
    import breachbench

    assert breachbench.__version__
    assert breachbench.SCHEMA_VERSION == "1.0"


def test_submodules_import_without_keys_or_network():
    # Importing every core subpackage must not touch a key or the network.
    import breachbench.config  # noqa: F401
    import breachbench.providers  # noqa: F401
    import breachbench.scenarios  # noqa: F401
    import breachbench.attacks  # noqa: F401
    import breachbench.detection  # noqa: F401
    import breachbench.judge  # noqa: F401
    import breachbench.loop  # noqa: F401
    import breachbench.runner  # noqa: F401
    import breachbench.recording  # noqa: F401


def test_experiment_config_loads():
    from breachbench.config import load_experiment_config

    cfg = load_experiment_config()
    assert cfg.k_max >= 1
    assert cfg.repetitions >= 1
    assert cfg.targets
    assert cfg.partial_min >= 1


def test_models_registry_loads_and_reports_capabilities():
    from breachbench.config import ModelSpec, Vendor, load_models_registry

    reg = load_models_registry()
    cap = reg.capability(ModelSpec(vendor=Vendor.GROQ, model_version="llama-3.1-8b-instant"))
    # This model is declared as lacking native tool support -> text-protocol fallback.
    assert cap.supports_native_tools is False


def test_resolve_api_key_raises_only_when_called():
    # No exception at import; the error surfaces only at resolution time.
    from breachbench.config import MissingAPIKeyError, resolve_api_key

    with pytest.raises(MissingAPIKeyError):
        resolve_api_key("OPENAI_API_KEY")

    # Non-raising probe returns False rather than raising.
    from breachbench.config import has_api_key

    assert has_api_key("OPENAI_API_KEY") is False
