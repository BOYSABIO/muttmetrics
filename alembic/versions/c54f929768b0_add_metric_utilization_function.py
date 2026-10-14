"""add metric_utilization function

Revision ID: c54f929768b0
Revises: f9ab2ca40a3a
Create Date: 2026-10-14 20:29:55.856208

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c54f929768b0"
down_revision: str | Sequence[str] | None = "f9ab2ca40a3a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION metric_utilization(buffer_minutes integer)
        RETURNS TABLE (
            visit_date date,
            n integer,
            planned_p50 integer,
            planned_p90 integer,
            actual_minutes integer,
            missing_prediction integer,
            over_buffer boolean
        )
        LANGUAGE sql
        STABLE
        AS $$
            SELECT
                v.visit_date,
                COUNT(*)::int AS n,
                COALESCE(SUM(v.predicted_min_p50), 0)::int AS planned_p50,
                COALESCE(SUM(v.predicted_min_p90), 0)::int AS planned_p90,
                COALESCE(SUM(v.actual_minutes), 0)::int AS actual_minutes,
                COUNT(*) FILTER (
                    WHERE v.predicted_min_p50 IS NULL
                )::int AS missing_prediction,
                (
                    COALESCE(SUM(v.predicted_min_p90), 0) > buffer_minutes
                ) AS over_buffer
            FROM visit v
            WHERE v.status IS NULL OR v.status = 'completed'
            GROUP BY v.visit_date
        $$
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS metric_utilization(integer)")
