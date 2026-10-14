"""add metric_eur_per_hour view

Revision ID: 963b2a16fbba
Revises: 8f648d320cb0
Create Date: 2026-10-14 15:30:26.579011

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "963b2a16fbba"
down_revision: str | Sequence[str] | None = "8f648d320cb0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE VIEW metric_eur_per_hour AS
        SELECT
            date_trunc('week', visit_date::timestamp)::date AS week_start,
            condition_score,
            shaved_down,
            COUNT(*)::int AS n,
            COALESCE(SUM(actual_minutes), 0)::int AS groomed_minutes,
            (COALESCE(SUM(actual_minutes), 0) / 60.0)::numeric AS hours,
            COALESCE(SUM(final_price), 0)::numeric AS revenue_ex_tip,
            COALESCE(
                SUM(final_price + COALESCE(tip, 0)),
                0
            )::numeric AS revenue_inc_tip,
            CASE
                WHEN COUNT(*) >= 5 THEN
                    (SUM(final_price) / (SUM(actual_minutes) / 60.0))::numeric
                ELSE NULL
            END AS eur_per_hour_ex_tip,
            CASE
                WHEN COUNT(*) >= 5 THEN
                    (SUM(final_price + COALESCE(tip, 0))
                     / (SUM(actual_minutes) / 60.0))::numeric
                ELSE NULL
            END AS eur_per_hour_inc_tip
        FROM visit
        WHERE (status IS NULL OR status = 'completed')
          AND final_price IS NOT NULL
          AND actual_minutes IS NOT NULL
          AND actual_minutes > 0
          AND condition_score IS NOT NULL
          AND shaved_down IS NOT NULL
        GROUP BY 1, 2, 3
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS metric_eur_per_hour")
