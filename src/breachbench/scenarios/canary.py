"""Seeded canary generation + persona rendering.

The canary is a uniformly random, semantically null token. Generation is fully
deterministic given (spec, seed) so a run is reproducible in structure and the
canary can be regenerated for audit. The token is meaningless — safe to store and
to match against in plaintext.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .schema import ScenarioSpec


@dataclass(frozen=True)
class RenderedTarget:
    """The Target's initialization for one run."""

    system_prompt: str
    canary: str | None  # the raw matchable token (wrapper stripped), or None for INTEGRITY


def generate_canary(alphabet: str, length: int, *, seed: int) -> str:
    rng = random.Random(seed)
    return "".join(rng.choice(alphabet) for _ in range(length))


def render_target(scenario: ScenarioSpec, *, canary_seed: int) -> RenderedTarget:
    """Produce the Target system prompt (and the matchable canary) for a run."""
    if scenario.canary.enabled:
        raw = generate_canary(scenario.canary.alphabet, scenario.canary.length, seed=canary_seed)
        displayed = scenario.canary.wrapper.format(value=raw)
        system_prompt = scenario.persona.template.format(canary=displayed, **scenario.persona.variables)
        # The matchable canary is the DISPLAYED form (incl. wrapper), because that is
        # exactly the string the Target would have to reveal. The matcher additionally
        # tolerates wrapper stripping via its normalization/transform set.
        return RenderedTarget(system_prompt=system_prompt, canary=displayed)

    # INTEGRITY (or canary-less) scenario: no canary placeholder to fill.
    system_prompt = scenario.persona.template.format(**scenario.persona.variables)
    return RenderedTarget(system_prompt=system_prompt, canary=None)
