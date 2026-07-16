"""Typed configuration models (pydantic v2).

These describe the *shape* of `config/experiment.yaml` and `config/models.yaml`.
Loading and validating them touches no network and reads no API key — a key is
resolved only later, lazily, when an adapter first makes a call.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Vendor(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    GROQ = "groq"
    STUB = "stub"  # offline deterministic provider, tests only


class AttackVector(str, Enum):
    ROLEPLAY = "ROLEPLAY"
    AUTHORITY = "AUTHORITY"
    CIPHER = "CIPHER"
    MANY_SHOT = "MANY_SHOT"


class BreachType(str, Enum):
    CONFIDENTIALITY = "CONFIDENTIALITY"
    INTEGRITY = "INTEGRITY"


class ModelSpec(BaseModel):
    """One (vendor, model_version) coordinate."""

    model_config = {"frozen": True}

    vendor: Vendor
    model_version: str

    def label(self) -> str:
        return f"{self.vendor.value}:{self.model_version}"


class RoleTemperatures(BaseModel):
    model_config = {"frozen": True}

    attacker: float = 1.0
    target: float = 0.7
    judge: float = 0.0


class JudgeConfig(BaseModel):
    model_config = {"frozen": True}

    enabled: bool = False
    vendor: Vendor = Vendor.OPENAI
    model_version: str = "gpt-4o-mini"


class RetryConfig(BaseModel):
    model_config = {"frozen": True}

    max_attempts: int = Field(default=5, ge=1)
    initial_backoff_s: float = Field(default=1.0, gt=0)
    max_backoff_s: float = Field(default=30.0, gt=0)
    timeout_s: float = Field(default=60.0, gt=0)


class ConcurrencyConfig(BaseModel):
    model_config = {"frozen": True}

    mode: Literal["sequential", "bounded"] = "sequential"
    max_workers: int = Field(default=1, ge=1)


class OutputConfig(BaseModel):
    model_config = {"frozen": True}

    dir: str = "output"
    transcript_dir: str = "runs"


class LogrankPair(BaseModel):
    """A pre-registered between-model comparison (matched scenario x vector)."""

    model_config = {"frozen": True}

    scenario_id: str
    attack_vector: AttackVector
    model_a: ModelSpec
    model_b: ModelSpec


class ExperimentConfig(BaseModel):
    """The full experiment grid + run parameters (`config/experiment.yaml`)."""

    model_config = {"frozen": True}

    schema_version: str = "1.0"
    master_seed: int
    k_max: int = Field(ge=1)
    repetitions: int = Field(ge=1)
    partial_min: int = Field(default=8, ge=1)

    temperatures: RoleTemperatures = RoleTemperatures()
    judge: JudgeConfig = JudgeConfig()

    attacker: ModelSpec
    targets: list[ModelSpec] = Field(min_length=1)
    scenarios: list[str] = Field(min_length=1)
    vectors: list[AttackVector] = Field(min_length=1)

    concurrency: ConcurrencyConfig = ConcurrencyConfig()
    retry: RetryConfig = RetryConfig()
    output: OutputConfig = OutputConfig()

    logrank_pairs: list[LogrankPair] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_attacker_not_in_targets(self) -> "ExperimentConfig":
        # A soft check: the grid enforces Attacker != Target per cell (skip/relabel),
        # but if EVERY target equals the attacker the grid would be empty — warn early.
        if self.targets and all(t == self.attacker for t in self.targets):
            raise ValueError(
                "Every target equals the configured attacker; the grid would be empty. "
                "Add at least one target distinct from the attacker."
            )
        return self


class ModelCapability(BaseModel):
    model_config = {"frozen": True}

    supports_native_tools: bool = True
    supports_seed: bool = False


class VendorRegistryEntry(BaseModel):
    model_config = {"frozen": True}

    api_key_env: str
    default: ModelCapability = ModelCapability()
    models: dict[str, ModelCapability] = Field(default_factory=dict)

    def capability_for(self, model_version: str) -> ModelCapability:
        return self.models.get(model_version, self.default)


class ModelsRegistry(BaseModel):
    """Parsed `config/models.yaml`: vendor -> capabilities + key env var."""

    model_config = {"frozen": True}

    vendors: dict[str, VendorRegistryEntry]

    def entry(self, vendor: Vendor | str) -> VendorRegistryEntry:
        key = vendor.value if isinstance(vendor, Vendor) else vendor
        if key not in self.vendors:
            raise KeyError(f"Vendor '{key}' not present in models.yaml registry.")
        return self.vendors[key]

    def capability(self, spec: ModelSpec) -> ModelCapability:
        return self.entry(spec.vendor).capability_for(spec.model_version)
