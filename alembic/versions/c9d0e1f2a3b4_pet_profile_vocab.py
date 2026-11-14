"""pet profile: fixed lists, size by eye, usual cut, one health box, change log (2026-11)

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-11-14

Makes the dog/cat profile clean enough to be model input later (M7, #121):
every field a model may use gets a fixed list the database enforces
(muttmetrics/pet_vocab.py), and docs/architecture/pet-data.md says why.

pet
  - coat_type: one groomer type per species, CHECKed. Existing values are
    mapped: dog 'single' -> 'silky'; cat 'smooth' -> 'short', 'double' ->
    'long'; anything else that isn't on the list -> NULL.
  - coat_thickness (new, 1 thin .. 3 thick), filled from coat_density
    (light / medium / dense).
  - size_band can now be picked by eye; size_source (new) says 'weight' or
    'eye'. Existing sizes: 'weight' if the pet has a weight, else 'eye'.
    Values outside s/m/l/xl -> NULL.
  - sex: 'female' / 'male' only ('f'/'w' -> female, 'm' -> male); 'unknown'
    and anything else -> NULL, since blank already means nobody checked.
  - usual_cut (new, free text).
  - health_notes (new) = mobility_notes + vet_notes joined.
  - hair_or_fur, coat_density, undercoat, sheds, mobility_notes, vet_notes:
    retired from the API, NOT dropped. A later migration drops them once the
    real values have been looked at.

breed
  - default_coat_type mapped and CHECKed like the pet's.
  - typical_size_band: 'xs' -> 's' (pricing has four bands), CHECKed.
  - source (new): 'catalog' (shipped with priors) or 'salon' (added in the
    shop). Existing rows are catalog.
  - unique (species, lower(name_en)). Upgrade stops with a clear message if
    two breeds already share a name.

pet_change (new): one row per tracked field a profile save changed.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c9d0e1f2a3b4"
down_revision: str | Sequence[str] | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Frozen copies of muttmetrics/pet_vocab.py as of this revision, so a later
# change to the lists needs its own migration instead of rewriting this one.
BREED_COAT_TYPE_CHECK_SQL = (
    "default_coat_type IS NULL OR (species = 'dog' AND default_coat_type IN"
    " ('smooth', 'double', 'curly', 'wire', 'silky', 'combination')) OR (sp"
    "ecies = 'cat' AND default_coat_type IN ('short', 'long'))"
)
BREED_SIZE_BAND_CHECK_SQL = (
    "typical_size_band IS NULL OR typical_size_band IN ('s', 'm', 'l', 'xl')"
)
BREED_SOURCE_CHECK_SQL = "source IN ('catalog', 'salon')"
PET_COAT_THICKNESS_CHECK_SQL = "coat_thickness IS NULL OR coat_thickness BETWEEN 1 AND 3"
PET_COAT_TYPE_CHECK_SQL = (
    "coat_type IS NULL OR (species = 'dog' AND coat_type IN ('smooth', 'dou"
    "ble', 'curly', 'wire', 'silky', 'combination')) OR (species = 'cat' AN"
    "D coat_type IN ('short', 'long'))"
)
PET_SEX_CHECK_SQL = "sex IS NULL OR sex IN ('female', 'male')"
PET_SIZE_BAND_CHECK_SQL = "size_band IS NULL OR size_band IN ('s', 'm', 'l', 'xl')"
PET_SIZE_SOURCE_CHECK_SQL = (
    "(size_band IS NULL AND size_source IS NULL) OR (size_band IS NOT NULL"
    " AND size_source IS NOT NULL AND size_source IN ('weight', 'eye'))"
)

DOG_TYPES = "('smooth', 'double', 'curly', 'wire', 'silky', 'combination')"
CAT_TYPES = "('short', 'long')"


def _map_coat(table: str, column: str) -> None:
    op.execute(f"UPDATE {table} SET {column} = lower(trim({column})) WHERE {column} IS NOT NULL")
    op.execute(
        f"UPDATE {table} SET {column} = 'silky' WHERE species = 'dog' AND {column} = 'single'"
    )
    op.execute(
        f"UPDATE {table} SET {column} = 'short' "
        f"WHERE species = 'cat' AND {column} IN ('smooth', 'single')"
    )
    op.execute(
        f"UPDATE {table} SET {column} = 'long' WHERE species = 'cat' AND {column} = 'double'"
    )
    op.execute(
        f"UPDATE {table} SET {column} = NULL WHERE {column} IS NOT NULL AND NOT ("
        f"(species = 'dog' AND {column} IN {DOG_TYPES}) OR "
        f"(species = 'cat' AND {column} IN {CAT_TYPES}))"
    )


def upgrade() -> None:
    conn = op.get_bind()

    # --- breed -----------------------------------------------------------------
    dupes = conn.execute(
        sa.text(
            "SELECT species, lower(name_en) AS name, count(*) FROM breed "
            "WHERE name_en IS NOT NULL GROUP BY 1, 2 HAVING count(*) > 1"
        )
    ).fetchall()
    if dupes:
        listed = ", ".join(f"{s}:{n} x{c}" for s, n, c in dupes)
        raise RuntimeError(
            f"Two breeds share an English name ({listed}). Merge them first "
            "(move pets to one breed_id, remove the spare row), then upgrade again."
        )

    op.add_column(
        "breed",
        sa.Column("source", sa.String(), nullable=False, server_default="catalog"),
    )
    _map_coat("breed", "default_coat_type")
    op.execute("UPDATE breed SET typical_size_band = 's' WHERE typical_size_band = 'xs'")
    op.execute(
        "UPDATE breed SET typical_size_band = NULL "
        "WHERE typical_size_band NOT IN ('s', 'm', 'l', 'xl')"
    )
    op.create_check_constraint("ck_breed_default_coat_type", "breed", BREED_COAT_TYPE_CHECK_SQL)
    op.create_check_constraint("ck_breed_typical_size_band", "breed", BREED_SIZE_BAND_CHECK_SQL)
    op.create_check_constraint("ck_breed_source", "breed", BREED_SOURCE_CHECK_SQL)
    op.create_index(
        "uq_breed_species_name_en",
        "breed",
        ["species", sa.text("lower(name_en)")],
        unique=True,
    )

    # --- pet -------------------------------------------------------------------
    op.add_column("pet", sa.Column("coat_thickness", sa.SmallInteger(), nullable=True))
    op.add_column("pet", sa.Column("size_source", sa.String(), nullable=True))
    op.add_column("pet", sa.Column("usual_cut", sa.Text(), nullable=True))
    op.add_column("pet", sa.Column("health_notes", sa.Text(), nullable=True))

    _map_coat("pet", "coat_type")
    op.execute(
        "UPDATE pet SET coat_thickness = CASE lower(trim(coat_density)) "
        "WHEN 'light' THEN 1 WHEN 'medium' THEN 2 WHEN 'dense' THEN 3 END "
        "WHERE coat_density IS NOT NULL"
    )
    op.execute("UPDATE pet SET size_band = lower(trim(size_band)) WHERE size_band IS NOT NULL")
    op.execute("UPDATE pet SET size_band = NULL WHERE size_band NOT IN ('s', 'm', 'l', 'xl')")
    op.execute(
        "UPDATE pet SET size_source = CASE WHEN weight_kg IS NOT NULL THEN 'weight' ELSE 'eye' END "
        "WHERE size_band IS NOT NULL"
    )
    op.execute("UPDATE pet SET sex = lower(trim(sex)) WHERE sex IS NOT NULL")
    # The old SQL recipe's example was 'F'.
    op.execute("UPDATE pet SET sex = 'female' WHERE sex IN ('f', 'w')")
    op.execute("UPDATE pet SET sex = 'male' WHERE sex = 'm'")
    op.execute("UPDATE pet SET sex = NULL WHERE sex NOT IN ('female', 'male')")
    op.execute(
        "UPDATE pet SET health_notes = NULLIF(concat_ws(E'\\n\\n', "
        "NULLIF(trim(mobility_notes), ''), NULLIF(trim(vet_notes), '')), '')"
    )

    op.create_check_constraint("ck_pet_coat_type", "pet", PET_COAT_TYPE_CHECK_SQL)
    op.create_check_constraint("ck_pet_coat_thickness", "pet", PET_COAT_THICKNESS_CHECK_SQL)
    op.create_check_constraint("ck_pet_size_band", "pet", PET_SIZE_BAND_CHECK_SQL)
    op.create_check_constraint("ck_pet_size_source", "pet", PET_SIZE_SOURCE_CHECK_SQL)
    op.create_check_constraint("ck_pet_sex", "pet", PET_SEX_CHECK_SQL)

    # --- pet_change ------------------------------------------------------------
    op.create_table(
        "pet_change",
        sa.Column("change_id", sa.Integer(), primary_key=True),
        sa.Column(
            "pet_id",
            sa.Integer(),
            sa.ForeignKey("pet.pet_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field", sa.String(), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_pet_change_pet_id_changed_at", "pet_change", ["pet_id", "changed_at"])


def downgrade() -> None:
    op.drop_index("ix_pet_change_pet_id_changed_at", table_name="pet_change")
    op.drop_table("pet_change")

    for name in (
        "ck_pet_sex",
        "ck_pet_size_source",
        "ck_pet_size_band",
        "ck_pet_coat_thickness",
        "ck_pet_coat_type",
    ):
        op.drop_constraint(name, "pet", type_="check")
    # Old code read 'single'; the other new types had no old spelling and stay.
    op.execute("UPDATE pet SET coat_type = 'single' WHERE coat_type = 'silky'")
    op.drop_column("pet", "health_notes")
    op.drop_column("pet", "usual_cut")
    op.drop_column("pet", "size_source")
    op.drop_column("pet", "coat_thickness")

    op.drop_index("uq_breed_species_name_en", table_name="breed")
    for name in ("ck_breed_source", "ck_breed_typical_size_band", "ck_breed_default_coat_type"):
        op.drop_constraint(name, "breed", type_="check")
    op.execute("UPDATE breed SET default_coat_type = 'single' WHERE default_coat_type = 'silky'")
    op.drop_column("breed", "source")
