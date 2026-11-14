"""The fixed lists a pet profile is described with (profile cleanup, 2026-11).

One place for the codes the database CHECKs, the API validates and the UI
labels. Words live in the frontend; the database stores these codes, so a
model (M7, #121) sees one spelling per meaning. See
``docs/architecture/pet-data.md`` for why each field exists.

Changing a list: edit it here, then add a migration that replaces the matching
CHECK (the SQL bodies below are what the migration uses).
"""

from __future__ import annotations

from typing import Literal

# --- Coat type ---------------------------------------------------------------
# The groomer's classification. One answer implies what used to be separate
# questions (hair vs fur, undercoat, sheds).
DOG_COAT_TYPES: tuple[str, ...] = (
    "smooth",  # short and close: Boxer, French Bulldog
    "double",  # undercoat, sheds: Husky, Golden, Lab, German Shepherd
    "curly",  # keeps growing, barely sheds, mats: Poodle, Bichon, doodles
    "wire",  # harsh coat, hand stripping: most terriers, Schnauzer
    "silky",  # long and silky, keeps growing: Yorkie, Maltese, Shih Tzu
    "combination",  # short on the body, feathering: Cocker, Setter
)
CAT_COAT_TYPES: tuple[str, ...] = ("short", "long")

COAT_TYPES_BY_SPECIES: dict[str, tuple[str, ...]] = {
    "dog": DOG_COAT_TYPES,
    "cat": CAT_COAT_TYPES,
}

CoatType = Literal["smooth", "double", "curly", "wire", "silky", "combination", "short", "long"]

# --- Coat thickness (ordinal) ------------------------------------------------
# 1 thin, 2 normal, 3 thick. How much coat there is to wash, dry and de-shed,
# which the breed alone doesn't tell you.
COAT_THICKNESS_MIN = 1
COAT_THICKNESS_MAX = 3

# --- Size ----------------------------------------------------------------------
SIZE_BANDS: tuple[str, ...] = ("s", "m", "l", "xl")
SizeBandCode = Literal["s", "m", "l", "xl"]

# Where size_band came from: computed from a weighed dog, or picked by eye.
# Different measurements; a model can weigh them differently.
SIZE_SOURCES: tuple[str, ...] = ("weight", "eye")

# --- Sex -----------------------------------------------------------------------
# Unknown is NULL (blank = nobody checked), not a third value.
SEXES: tuple[str, ...] = ("female", "male")
Sex = Literal["female", "male"]

# --- Breed origin ----------------------------------------------------------------
# catalog = shipped with the app (has priors); salon = added in the shop.
BREED_SOURCES: tuple[str, ...] = ("catalog", "salon")

# --- What the change log tracks -------------------------------------------------
# Structured facts a model may use, so it can ask "what did we know on the
# visit date?". Names and free-text notes are deliberately NOT logged: they
# are personal data and erase (ops/client_erase.py) scrubs them in place.
TRACKED_PET_FIELDS: tuple[str, ...] = (
    "species",
    "breed_id",
    "breed_secondary_id",
    "sex",
    "weight_kg",
    "size_band",
    "size_source",
    "coat_type",
    "coat_thickness",
    "handling_score",
    "muzzle_required",
    "two_person_job",
    "senior_flag",
)


def _in_list(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


# Postgres CHECK bodies (used by the model and the migration).
PET_COAT_TYPE_CHECK_SQL = (
    "coat_type IS NULL"
    f" OR (species = 'dog' AND {_in_list('coat_type', DOG_COAT_TYPES)})"
    f" OR (species = 'cat' AND {_in_list('coat_type', CAT_COAT_TYPES)})"
)
BREED_COAT_TYPE_CHECK_SQL = (
    "default_coat_type IS NULL"
    f" OR (species = 'dog' AND {_in_list('default_coat_type', DOG_COAT_TYPES)})"
    f" OR (species = 'cat' AND {_in_list('default_coat_type', CAT_COAT_TYPES)})"
)
PET_COAT_THICKNESS_CHECK_SQL = (
    "coat_thickness IS NULL OR coat_thickness"
    f" BETWEEN {COAT_THICKNESS_MIN} AND {COAT_THICKNESS_MAX}"
)
PET_SIZE_BAND_CHECK_SQL = f"size_band IS NULL OR {_in_list('size_band', SIZE_BANDS)}"
BREED_SIZE_BAND_CHECK_SQL = (
    f"typical_size_band IS NULL OR {_in_list('typical_size_band', SIZE_BANDS)}"
)
# A size always says where it came from, and a source never floats alone.
# (IS NOT NULL spelled out: a CHECK passes when it evaluates to NULL.)
PET_SIZE_SOURCE_CHECK_SQL = (
    "(size_band IS NULL AND size_source IS NULL)"
    " OR (size_band IS NOT NULL AND size_source IS NOT NULL"
    f" AND {_in_list('size_source', SIZE_SOURCES)})"
)
PET_SEX_CHECK_SQL = f"sex IS NULL OR {_in_list('sex', SEXES)}"
BREED_SOURCE_CHECK_SQL = _in_list("source", BREED_SOURCES)
