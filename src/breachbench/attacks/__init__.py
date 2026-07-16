"""Attack taxonomy: vector registry, per-vector strategies, and the Attacker agent."""

from .attacker import Attacker, AttackerTurn, build_grey_box_brief
from .base import AttackVectorStrategy, GreyBoxBrief, Turn
from .registry import REGISTRY, VectorMeta, get_meta, list_vectors

__all__ = [
    "REGISTRY",
    "AttackVectorStrategy",
    "Attacker",
    "AttackerTurn",
    "GreyBoxBrief",
    "Turn",
    "VectorMeta",
    "build_grey_box_brief",
    "get_meta",
    "list_vectors",
]
