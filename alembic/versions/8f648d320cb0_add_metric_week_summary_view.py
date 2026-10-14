"""add metric_week_summary view

Revision ID: 8f648d320cb0
Revises: ddf104db6342
Create Date: 2026-10-14 08:10:37.554986

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f648d320cb0"
down_revision: str | Sequence[str] | None = "ddf104db6342"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE VIEW metric_week_summary AS
        SELECT
            date_trunc('week', visit_date::timestamp)::date AS week_start,
            COUNT(*)::int AS visit_count,
            COALESCE(SUM(actual_minutes), 0)::int AS groomed_minutes,
            COALESCE(SUM(final_price), 0)::numeric AS revenue_ex_tip,
            COALESCE(
                SUM(
                    CASE
                        WHEN final_price IS NOT NULL
                        THEN final_price + COALESCE(tip, 0)
                    END
                ),
                0
            )::numeric AS revenue_inc_tip
        FROM visit
        WHERE status IS NULL OR status = 'completed'
        GROUP BY 1
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS metric_week_summary")
