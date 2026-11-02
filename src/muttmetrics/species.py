"""Allowed animal species — one list for CHECK, API, and seed (#190 / ADR-004).

Adding a species: extend this tuple, amend the matching Postgres CHECKs
in a migration, seed breeds, optional size bands in priors/size.py.
"""

from typing import Literal

ALLOWED_SPECIES: tuple[str, ...] = ("dog", "cat")
DEFAULT_SPECIES = "dog"

Species = Literal["dog", "cat"]

# Postgres CHECK bodies — keep in lockstep with ALLOWED_SPECIES.
SPECIES_CHECK_SQL = "species IN ('dog', 'cat')"
SERVICE_SPECIES_CHECK_SQL = "species IS NULL OR species IN ('dog', 'cat')"
