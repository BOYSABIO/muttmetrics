"""rename dog → pet; add species on pet/breed/service (#190)

Revision ID: e1a2b3c4d5e6
Revises: d8e9f0a1b2c3
Create Date: 2026-11-02

RENAME preserves rows. Species columns default to 'dog' for existing data.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from muttmetrics.species import (
    DEFAULT_SPECIES,
    SERVICE_SPECIES_CHECK_SQL,
    SPECIES_CHECK_SQL,
)

revision: str = "e1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "d8e9f0a1b2c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Rename dog → pet (data kept); add species discriminators."""
    op.rename_table("dog", "pet")
    op.alter_column("pet", "dog_id", new_column_name="pet_id")
    op.execute("ALTER SEQUENCE IF EXISTS dog_dog_id_seq RENAME TO pet_pet_id_seq")
    op.execute("ALTER INDEX IF EXISTS ix_dog_owner_id RENAME TO ix_pet_owner_id")
    op.execute("ALTER INDEX IF EXISTS ix_dog_breed_id RENAME TO ix_pet_breed_id")
    op.execute(
        "ALTER INDEX IF EXISTS ix_dog_breed_secondary_id RENAME TO ix_pet_breed_secondary_id"
    )
    op.execute("ALTER TABLE pet RENAME CONSTRAINT ck_dog_handling_score TO ck_pet_handling_score")

    op.alter_column("visit", "dog_id", new_column_name="pet_id")
    op.execute("ALTER INDEX IF EXISTS ix_visit_dog_id RENAME TO ix_visit_pet_id")

    op.alter_column("photo", "dog_id", new_column_name="pet_id")
    op.execute("ALTER INDEX IF EXISTS ix_photo_dog_id_kind RENAME TO ix_photo_pet_id_kind")

    op.add_column(
        "pet",
        sa.Column(
            "species",
            sa.String(),
            nullable=False,
            server_default=DEFAULT_SPECIES,
        ),
    )
    op.create_check_constraint("ck_pet_species", "pet", SPECIES_CHECK_SQL)

    op.add_column(
        "breed",
        sa.Column(
            "species",
            sa.String(),
            nullable=False,
            server_default=DEFAULT_SPECIES,
        ),
    )
    op.create_check_constraint("ck_breed_species", "breed", SPECIES_CHECK_SQL)

    op.add_column("service", sa.Column("species", sa.String(), nullable=True))
    op.create_check_constraint("ck_service_species", "service", SERVICE_SPECIES_CHECK_SQL)


def downgrade() -> None:
    """Restore dog table name; drop species columns."""
    op.drop_constraint("ck_service_species", "service", type_="check")
    op.drop_column("service", "species")
    op.drop_constraint("ck_breed_species", "breed", type_="check")
    op.drop_column("breed", "species")
    op.drop_constraint("ck_pet_species", "pet", type_="check")
    op.drop_column("pet", "species")

    op.execute("ALTER INDEX IF EXISTS ix_photo_pet_id_kind RENAME TO ix_photo_dog_id_kind")
    op.alter_column("photo", "pet_id", new_column_name="dog_id")
    op.execute("ALTER INDEX IF EXISTS ix_visit_pet_id RENAME TO ix_visit_dog_id")
    op.alter_column("visit", "pet_id", new_column_name="dog_id")

    op.execute("ALTER TABLE pet RENAME CONSTRAINT ck_pet_handling_score TO ck_dog_handling_score")
    op.execute(
        "ALTER INDEX IF EXISTS ix_pet_breed_secondary_id RENAME TO ix_dog_breed_secondary_id"
    )
    op.execute("ALTER INDEX IF EXISTS ix_pet_breed_id RENAME TO ix_dog_breed_id")
    op.execute("ALTER INDEX IF EXISTS ix_pet_owner_id RENAME TO ix_dog_owner_id")
    op.execute("ALTER SEQUENCE IF EXISTS pet_pet_id_seq RENAME TO dog_dog_id_seq")
    op.alter_column("pet", "pet_id", new_column_name="dog_id")
    op.rename_table("pet", "dog")
