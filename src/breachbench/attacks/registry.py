"""Attack-vector taxonomy registry — enumerable and extensible.

New vectors register here. `induces_encodings` (for CIPHER) MUST be a subset of the
detection transform registry so the detector never lags the attack; a test enforces
this coupling.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config.schema import AttackVector
from .base import AttackVectorStrategy
from .strategies import AUTHORITY, CIPHER, MANY_SHOT, ROLEPLAY


@dataclass(frozen=True)
class VectorMeta:
    vector: AttackVector
    display_name: str
    description: str
    strategy: AttackVectorStrategy
    # Encodings this vector may induce; must be a subset of detection TRANSFORM_NAMES.
    induces_encodings: tuple[str, ...] = field(default_factory=tuple)


REGISTRY: dict[AttackVector, VectorMeta] = {
    AttackVector.ROLEPLAY: VectorMeta(
        vector=AttackVector.ROLEPLAY,
        display_name="Roleplay / fictional framing",
        description="Fictional or persona frame that makes disclosure feel in-character.",
        strategy=ROLEPLAY,
    ),
    AttackVector.AUTHORITY: VectorMeta(
        vector=AttackVector.AUTHORITY,
        display_name="Authority / social pressure",
        description="Impersonated authority asserts override permission or urgency.",
        strategy=AUTHORITY,
    ),
    AttackVector.CIPHER: VectorMeta(
        vector=AttackVector.CIPHER,
        display_name="Cipher / indirect encoding",
        description="Elicit the secret via a trivial reversible encoding.",
        strategy=CIPHER,
        # Kept in lockstep with detection/transforms.py TRANSFORM_NAMES.
        induces_encodings=("spacing", "reverse", "rot13", "base64", "leetspeak"),
    ),
    AttackVector.MANY_SHOT: VectorMeta(
        vector=AttackVector.MANY_SHOT,
        display_name="Many-shot priming",
        description="Many compliant examples prime the Target to continue the pattern.",
        strategy=MANY_SHOT,
    ),
}


def get_meta(vector: AttackVector) -> VectorMeta:
    return REGISTRY[vector]


def list_vectors() -> list[AttackVector]:
    return list(REGISTRY.keys())
