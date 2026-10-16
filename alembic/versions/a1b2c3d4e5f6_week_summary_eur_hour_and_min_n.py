"""week summary overall €/hour + metric_constants.min_n

Revision ID: a1b2c3d4e5f6
Revises: c54f929768b0
Create Date: 2026-10-16

Adds overall (week) €/hour rates to metric_week_summary with MIN_N in SQL,
and metric_constants so the API can expose min_n without a second threshold.

# migration-safety: reviewed - DROP VIEW metric_week_summary only (no table data);
# recreate with eur_per_hour_* columns for #158, see #158
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "c54f929768b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE VIEW metric_constants AS
        SELECT 5::int AS min_n
        """
    )
    op.execute("DROP VIEW IF EXISTS metric_week_summary")
    op.execute(
        """
        CREATE VIEW metric_week_summary AS
        WITH week_totals AS (
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
        ),
        week_eur AS (
            SELECT
                date_trunc('week', visit_date::timestamp)::date AS week_start,
                COUNT(*)::int AS eur_per_hour_n,
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
            GROUP BY 1
        )
        SELECT
            t.week_start,
            t.visit_count,
            t.groomed_minutes,
            t.revenue_ex_tip,
            t.revenue_inc_tip,
            COALESCE(e.eur_per_hour_n, 0)::int AS eur_per_hour_n,
            e.eur_per_hour_ex_tip,
            e.eur_per_hour_inc_tip
        FROM week_totals t
        LEFT JOIN week_eur e ON e.week_start = t.week_start
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS metric_week_summary")
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
    op.execute("DROP VIEW IF EXISTS metric_constants")
