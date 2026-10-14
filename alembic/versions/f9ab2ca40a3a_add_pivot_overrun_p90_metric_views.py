"""add pivot overrun p90 metric views

Revision ID: f9ab2ca40a3a
Revises: 963b2a16fbba
Create Date: 2026-10-14 19:59:42.306906

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9ab2ca40a3a"
down_revision: str | Sequence[str] | None = "963b2a16fbba"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE VIEW metric_pivot_rate AS
        SELECT
            date_trunc('week', visit_date::timestamp)::date AS week_start,
            COUNT(*)::int AS n,
            COUNT(*) FILTER (WHERE pivoted IS TRUE)::int AS pivoted_count,
            CASE
                WHEN COUNT(*) >= 5 THEN
                    (COUNT(*) FILTER (WHERE pivoted IS TRUE)::numeric / COUNT(*))
                ELSE NULL
            END AS pivot_rate
        FROM visit
        WHERE status IS NULL OR status = 'completed'
        GROUP BY 1

        UNION ALL

        SELECT
            NULL::date AS week_start,
            COUNT(*)::int AS n,
            COUNT(*) FILTER (WHERE pivoted IS TRUE)::int AS pivoted_count,
            CASE
                WHEN COUNT(*) >= 5 THEN
                    (COUNT(*) FILTER (WHERE pivoted IS TRUE)::numeric / COUNT(*))
                ELSE NULL
            END AS pivot_rate
        FROM visit
        WHERE status IS NULL OR status = 'completed'
        """
    )

    op.execute(
        """
        CREATE VIEW metric_overrun AS
        SELECT
            date_trunc('week', visit_date::timestamp)::date AS week_start,
            COUNT(*)::int AS n,
            CASE
                WHEN COUNT(*) >= 5 THEN
                    AVG(actual_minutes - predicted_min_p50)::numeric
                ELSE NULL
            END AS avg_overrun_minutes
        FROM visit
        WHERE (status IS NULL OR status = 'completed')
          AND predicted_min_p50 IS NOT NULL
          AND actual_minutes IS NOT NULL
        GROUP BY 1

        UNION ALL

        SELECT
            NULL::date,
            COUNT(*)::int,
            CASE
                WHEN COUNT(*) >= 5 THEN
                    AVG(actual_minutes - predicted_min_p50)::numeric
                ELSE NULL
            END
        FROM visit
        WHERE (status IS NULL OR status = 'completed')
          AND predicted_min_p50 IS NOT NULL
          AND actual_minutes IS NOT NULL
        """
    )

    op.execute(
        """
        CREATE VIEW metric_p90_miss AS
        SELECT
            date_trunc('week', visit_date::timestamp)::date AS week_start,
            COUNT(*)::int AS n,
            COUNT(*) FILTER (
                WHERE actual_minutes > predicted_min_p90
            )::int AS miss_count,
            CASE
                WHEN COUNT(*) >= 5 THEN
                    (COUNT(*) FILTER (
                        WHERE actual_minutes > predicted_min_p90
                    )::numeric / COUNT(*))
                ELSE NULL
            END AS miss_rate
        FROM visit
        WHERE (status IS NULL OR status = 'completed')
          AND predicted_min_p90 IS NOT NULL
          AND actual_minutes IS NOT NULL
        GROUP BY 1

        UNION ALL

        SELECT
            NULL::date,
            COUNT(*)::int,
            COUNT(*) FILTER (
                WHERE actual_minutes > predicted_min_p90
            )::int,
            CASE
                WHEN COUNT(*) >= 5 THEN
                    (COUNT(*) FILTER (
                        WHERE actual_minutes > predicted_min_p90
                    )::numeric / COUNT(*))
                ELSE NULL
            END
        FROM visit
        WHERE (status IS NULL OR status = 'completed')
          AND predicted_min_p90 IS NOT NULL
          AND actual_minutes IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS metric_p90_miss")
    op.execute("DROP VIEW IF EXISTS metric_overrun")
    op.execute("DROP VIEW IF EXISTS metric_pivot_rate")
