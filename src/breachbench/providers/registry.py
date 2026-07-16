"""Vendor -> adapter factory.

`build_provider` constructs the adapter object (cheap) but NOT the underlying SDK
client — that stays lazy inside the adapter. Adapter modules are imported lazily
by vendor so importing this registry never pulls in a vendor SDK.
"""

from __future__ import annotations

from ..config.schema import ModelSpec, ModelsRegistry, RetryConfig, Vendor
from .base import ChatProvider


def build_provider(
    spec: ModelSpec,
    *,
    models_registry: ModelsRegistry | None = None,
    retry: RetryConfig | None = None,
) -> ChatProvider:
    """Return a ChatProvider for `spec`, wiring key-env + capabilities from the
    models registry when available."""
    vendor = spec.vendor

    # Capability + key env come from models.yaml when present; otherwise defaults.
    api_key_env = None
    supports_native_tools = True
    supports_seed = vendor == Vendor.OPENAI
    if models_registry is not None and vendor.value in models_registry.vendors:
        entry = models_registry.entry(vendor)
        api_key_env = entry.api_key_env
        cap = entry.capability_for(spec.model_version)
        supports_native_tools = cap.supports_native_tools
        supports_seed = cap.supports_seed

    if vendor == Vendor.STUB:
        raise ValueError(
            "StubProvider cannot be built from the registry; instantiate it directly "
            "with a responder in tests."
        )

    if vendor == Vendor.OPENAI:
        from .openai_adapter import OpenAIAdapter

        return OpenAIAdapter(
            api_key_env=api_key_env or "OPENAI_API_KEY",
            retry=retry,
            supports_native_tools=supports_native_tools,
            supports_seed=supports_seed,
        )

    if vendor == Vendor.GEMINI:
        from .gemini_adapter import GeminiAdapter

        return GeminiAdapter(
            api_key_env=api_key_env or "GEMINI_API_KEY",
            retry=retry,
            supports_native_tools=supports_native_tools,
            supports_seed=supports_seed,
        )

    if vendor == Vendor.GROQ:
        from .groq_adapter import GroqAdapter

        return GroqAdapter(
            api_key_env=api_key_env or "GROQ_API_KEY",
            retry=retry,
            supports_native_tools=supports_native_tools,
            supports_seed=supports_seed,
        )

    raise ValueError(f"Unknown vendor: {vendor}")
