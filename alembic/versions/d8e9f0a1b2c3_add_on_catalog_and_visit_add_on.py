"""add_on catalog + visit_add_on; drop unused visit.add_ons (#192)

Revision ID: d8e9f0a1b2c3
Revises: c4d5e6f7a8b9
Create Date: 2026-10-29

Option A: typed catalog and join table so techniques are queryable.
The original visit.add_ons TEXT[] was never used in the app — drop it so
there is one way to record add-ons.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d8e9f0a1b2c3"
down_revision: str | Sequence[str] | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create add_on + visit_add_on; drop unused visit.add_ons array."""
    op.create_table(
        "add_on",
        sa.Column("add_on_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name_de", sa.String(), nullable=True),
        sa.Column("name_en", sa.String(), nullable=True),
        sa.Column("pricing", sa.String(), nullable=False),
        sa.Column("price_base", sa.Numeric(), nullable=True),
        sa.CheckConstraint("pricing IN ('flat', 'per_hour')", name="ck_add_on_pricing"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "visit_add_on",
        sa.Column("visit_id", sa.Integer(), nullable=False),
        sa.Column("add_on_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["visit_id"], ["visit.visit_id"]),
        sa.ForeignKeyConstraint(["add_on_id"], ["add_on.add_on_id"]),
        sa.PrimaryKeyConstraint("visit_id", "add_on_id"),
    )
    op.drop_column("visit", "add_ons")


def downgrade() -> None:
    """Restore empty add_ons array; drop join + catalog (join rows are lost)."""
    op.add_column(
        "visit",
        sa.Column(
            "add_ons",
            postgresql.ARRAY(sa.TEXT()),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.drop_table("visit_add_on")
    op.drop_table("add_on")


# Drop unused visit.add_ons; add_on + visit_add_on are the source of truth (#192)
# migration-safety: reviewed
