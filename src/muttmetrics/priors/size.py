"""Map weight_kg -> size_band (#171). Pure - no DB."""

from __future__ import annotations

from typing import Literal

SizeBand = Literal["s", "m", "l", "xl"]


# Inclusive tops from client pricing
SIZE_S_MAX_KG = 10.0
SIZE_M_MAX_KG = 26.0
SIZE_L_MAX_KG = 45.0


def size_band_from_weight(weight_kg: float | None) -> SizeBand | None:
    """Return s/m/l/xl from weight, or None if unknown / invalid."""
    if weight_kg is None or weight_kg <= 0:
        return None
    if weight_kg <= SIZE_S_MAX_KG:
        return "s"
    if weight_kg <= SIZE_M_MAX_KG:
        return "m"
    if weight_kg <= SIZE_L_MAX_KG:
        return "l"
    return "xl"
