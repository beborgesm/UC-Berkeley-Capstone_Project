"""Scenario / persona data model.

A scenario is DATA (a YAML file), not code: a persona system-prompt template plus
either a canary spec (CONFIDENTIALITY) or a forbidden-tool spec (INTEGRITY). New
scenarios are new files.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from ..config.schema import BreachType


class PersonaTemplate(BaseModel):
    model_config = {"frozen": True}

    template: str
    variables: dict[str, str] = Field(default_factory=dict)

    def has_canary_placeholder(self) -> bool:
        return "{canary}" in self.template


class CanarySpec(BaseModel):
    model_config = {"frozen": True}

    enabled: bool = False
    length: int = Field(default=16, ge=4, le=128)
    alphabet: str = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    wrapper: str = "{value}"  # e.g. "AX-{value}"; matcher strips the wrapper too

    @model_validator(mode="after")
    def _check(self) -> "CanarySpec":
        if self.enabled:
            if len(set(self.alphabet)) < 2:
                raise ValueError("canary alphabet must have at least 2 distinct chars")
            if "{value}" not in self.wrapper:
                raise ValueError("canary wrapper must contain '{value}'")
        return self


class ForbiddenToolSpec(BaseModel):
    model_config = {"frozen": True}

    enabled: bool = False
    name: str = "execute_emergency_override"
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}})
    authorization: str = "none"  # never issued in scope


class ScenarioSpec(BaseModel):
    model_config = {"frozen": True}

    scenario_id: str
    breach_type: BreachType
    persona: PersonaTemplate
    canary: CanarySpec = CanarySpec()
    forbidden_tool: ForbiddenToolSpec = ForbiddenToolSpec()
    notes: str = ""

    @model_validator(mode="after")
    def _consistency(self) -> "ScenarioSpec":
        if self.breach_type == BreachType.CONFIDENTIALITY:
            if not self.canary.enabled:
                raise ValueError(f"{self.scenario_id}: CONFIDENTIALITY scenario needs canary.enabled")
            if not self.persona.has_canary_placeholder():
                raise ValueError(
                    f"{self.scenario_id}: persona template must contain '{{canary}}' placeholder"
                )
        if self.breach_type == BreachType.INTEGRITY:
            if not self.forbidden_tool.enabled:
                raise ValueError(
                    f"{self.scenario_id}: INTEGRITY scenario needs forbidden_tool.enabled"
                )
            if self.forbidden_tool.authorization != "none":
                raise ValueError(
                    f"{self.scenario_id}: forbidden_tool.authorization must be 'none' (never issued)"
                )
        return self
