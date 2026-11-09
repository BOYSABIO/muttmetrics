"""visit.created_at: when the row was saved (#224)

Revision ID: f3a4b5c6d7e8
Revises: e1a2b3c4d5e6
Create Date: 2026-11-08

The groomer can choose a visit date in the past, so a visit added weeks later
looks exactly like one logged on the day. ``created_at`` records when the row
was saved, so the two can be told apart (compliance, data quality).

Two steps on purpose. ``ADD COLUMN ... DEFAULT now()`` would stamp every
EXISTING row with the moment this migration runs, which is a lie: nobody knows
when those were saved. So the column is added with no default (existing rows
stay NULL = "unknown"), and only then gets ``DEFAULT now()`` for new rows.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3a4b5c6d7e8"
down_revision: str | Sequence[str] | None = "e1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("visit", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("visit", "created_at", server_default=sa.text("now()"))


def downgrade() -> None:
    op.drop_column("visit", "created_at")
