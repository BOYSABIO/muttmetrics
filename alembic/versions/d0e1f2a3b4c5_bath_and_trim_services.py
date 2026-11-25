"""services: Bath and Trim on their own (2026-11)

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-11-25

The groomer sometimes does only a bath or only a trim, so both become
services next to "Bath and trim". About an hour each by his estimate, before
size and coat. Offered for every species (species NULL), no catalog price
(price_base stays NULL; data/private/pricing.json fills it where it exists).

Rows are added here, not only in the seed, so a deploy puts them on the box
without running the seed there. Existing rows with the same slug are left
alone, so a later seed run and this migration agree.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d0e1f2a3b4c5"
down_revision: str | Sequence[str] | None = "c9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Frozen copy of the two seed rows as of this revision.
NEW_SERVICES = (
    ("bath", "Baden", "Bath", 60, 15),
    ("trim", "Scheren", "Trim", 60, 15),
)


def upgrade() -> None:
    for slug, name_de, name_en, minutes, buffer in NEW_SERVICES:
        op.execute(
            f"""
            INSERT INTO service (slug, name_de, name_en, species, base_minutes, buffer_minutes)
            SELECT '{slug}', '{name_de}', '{name_en}', NULL, {minutes}, {buffer}
            WHERE NOT EXISTS (SELECT 1 FROM service WHERE slug = '{slug}')
            """
        )


def downgrade() -> None:
    # Only rows no visit points at: a downgrade must never drop logged work.
    for slug, *_ in NEW_SERVICES:
        op.execute(
            f"""
            DELETE FROM service s
            WHERE s.slug = '{slug}'
              AND NOT EXISTS (
                  SELECT 1 FROM visit v
                  WHERE v.booked_service_id = s.service_id
                     OR v.actual_service_id = s.service_id
              )
            """
        )
