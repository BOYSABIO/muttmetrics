"""metric_estimate_bands: where each groom landed against its estimate (2026-11-14)

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-11-14

The timing card showed an average overrun and a P90 miss rate. Neither says
how grooms are spread: this function counts, for visits with both estimates,
how many finished within the typical time (actual <= P50), took longer but
stayed within the worst case (P50 < actual <= P90), or went past it
(actual > P90). Counts are facts; ``enough`` says whether n >= MIN_N, so the
screen only draws proportions when they mean something. Definition:
docs/runbooks/analytics.md ("Estimate bands").
"""

from collections.abc import Sequence

from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: str | Sequence[str] | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION metric_estimate_bands(p_start date, p_end date)
        RETURNS TABLE (
            n integer,
            within_p50 integer,
            within_p90 integer,
            past_p90 integer,
            enough boolean
        )
        LANGUAGE sql
        STABLE
        AS $$
            SELECT
                COUNT(*)::int AS n,
                COUNT(*) FILTER (WHERE actual_minutes <= predicted_min_p50)::int,
                COUNT(*) FILTER (
                    WHERE actual_minutes > predicted_min_p50
                      AND actual_minutes <= predicted_min_p90
                )::int,
                COUNT(*) FILTER (WHERE actual_minutes > predicted_min_p90)::int,
                COUNT(*) >= (SELECT min_n FROM metric_constants)
            FROM visit
            WHERE (status IS NULL OR status = 'completed')
              AND predicted_min_p50 IS NOT NULL
              AND predicted_min_p90 IS NOT NULL
              AND actual_minutes IS NOT NULL
              AND visit_date >= p_start
              AND visit_date <= p_end
        $$
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS metric_estimate_bands(date, date)")
