"""metric_utilization_weeks: weekly rollup of the per-day function (#178)

Revision ID: c4d5e6f7a8b9
Revises: b7e8f9a0c1d2
Create Date: 2026-10-17

The month view used to add days up into weeks in the browser, which put a
formula in the frontend (against #158 / ADR-003) and invited comparing weekly
totals with the *daily* cap. This function reads metric_utilization, so
"what is a day" stays defined once, and only does the grouping.

``over_buffer_days`` counts days over the cap. A weekly total is never
compared with the daily cap.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: str | Sequence[str] | None = "b7e8f9a0c1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION metric_utilization_weeks(
            buffer_minutes integer,
            p_start date,
            p_end date
        )
        RETURNS TABLE (
            week_start date,
            range_start date,
            range_end date,
            day_count integer,
            n integer,
            planned_p50 integer,
            planned_p90 integer,
            actual_minutes integer,
            missing_prediction integer,
            over_buffer_days integer
        )
        LANGUAGE sql
        STABLE
        AS $$
            -- One row per ISO week (Monday) that has visits in the range.
            -- range_start / range_end clip the week to the requested range, so
            -- the first week of April reads "Apr 1-5", not "Mar 30-Apr 5".
            WITH days AS (
                SELECT
                    u.*,
                    date_trunc('week', u.visit_date::timestamp)::date AS wk
                FROM metric_utilization(buffer_minutes, p_start, p_end) u
            )
            SELECT
                d.wk,
                GREATEST(d.wk, p_start),
                LEAST(d.wk + 6, p_end),
                COUNT(*)::int,
                SUM(d.n)::int,
                SUM(d.planned_p50)::int,
                SUM(d.planned_p90)::int,
                SUM(d.actual_minutes)::int,
                SUM(d.missing_prediction)::int,
                COUNT(*) FILTER (WHERE d.over_buffer)::int
            FROM days d
            GROUP BY d.wk
            ORDER BY d.wk
        $$
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS metric_utilization_weeks(integer, date, date)")
