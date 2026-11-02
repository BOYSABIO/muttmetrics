"""Map weight_kg + species -> size_band (#171 / #190). Pure - no DB."""

from __future__ import annotations

from typing import Literal

from muttmetrics.species import DEFAULT_SPECIES

# The one definition of a size band; prior.py imports it from here.
SizeBand = Literal["s", "m", "l", "xl"]

# Inclusive tops from client pricing (dogs, #171)
DOG_SIZE_S_MAX_KG = 10.0
DOG_SIZE_M_MAX_KG = 26.0
DOG_SIZE_L_MAX_KG = 45.0

# Provisional cat bands (ADR-004) — confirm with the groomer.
CAT_SIZE_S_MAX_KG = 4.0
CAT_SIZE_M_MAX_KG = 5.5
CAT_SIZE_L_MAX_KG = 7.5

# species → (s_max, m_max, l_max). Omit a species = no size multiplier
# (same as unknown weight) until we have a scale.
_CUTOFFS: dict[str, tuple[float, float, float]] = {
    "dog": (DOG_SIZE_S_MAX_KG, DOG_SIZE_M_MAX_KG, DOG_SIZE_L_MAX_KG),
    "cat": (CAT_SIZE_S_MAX_KG, CAT_SIZE_M_MAX_KG, CAT_SIZE_L_MAX_KG),
}


def size_band_from_weight(
    weight_kg: float | None,
    species: str = DEFAULT_SPECIES,
) -> SizeBand | None:
    """Return s/m/l/xl from weight + species, or None if unknown / invalid."""
    if weight_kg is None or weight_kg <= 0:
        return None
    cutoffs = _CUTOFFS.get(species)
    if cutoffs is None:
        return None
    s_max, m_max, l_max = cutoffs
    if weight_kg <= s_max:
        return "s"
    if weight_kg <= m_max:
        return "m"
    if weight_kg <= l_max:
        return "l"
    return "xl"
