"""Configuration layer: typed schema, YAML loading, lazy secret resolution."""

from .loader import (
    DEFAULT_EXPERIMENT_PATH,
    DEFAULT_MODELS_PATH,
    load_experiment_config,
    load_models_registry,
)
from .schema import (
    AttackVector,
    BreachType,
    ConcurrencyConfig,
    ExperimentConfig,
    JudgeConfig,
    LogrankPair,
    ModelCapability,
    ModelSpec,
    ModelsRegistry,
    OutputConfig,
    RetryConfig,
    RoleTemperatures,
    Vendor,
    VendorRegistryEntry,
)
from .settings import (
    MissingAPIKeyError,
    has_api_key,
    resolve_api_key,
)

__all__ = [
    "AttackVector",
    "BreachType",
    "ConcurrencyConfig",
    "DEFAULT_EXPERIMENT_PATH",
    "DEFAULT_MODELS_PATH",
    "ExperimentConfig",
    "JudgeConfig",
    "LogrankPair",
    "MissingAPIKeyError",
    "ModelCapability",
    "ModelSpec",
    "ModelsRegistry",
    "OutputConfig",
    "RetryConfig",
    "RoleTemperatures",
    "Vendor",
    "VendorRegistryEntry",
    "has_api_key",
    "load_experiment_config",
    "load_models_registry",
    "resolve_api_key",
]
