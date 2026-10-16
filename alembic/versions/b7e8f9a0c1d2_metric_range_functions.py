"""metric range functions (week or month or custom) (#170)

Revision ID: b7e8f9a0c1d2
Revises: a1b2c3d4e5f6
Create Date: 2026-10-16

Replace week-grouped views with (p_start, p_end) functions so one definition
serves week, month, or any inclusive range. MIN_N from metric_constants.

# migration-safety: reviewed - DROP VIEW of metric_* views only (no table data);
# replace with range functions for #170
"""

from collections.abc import Sequence

from alembic import op

revision: str = "b7e8f9a0c1d2"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP VIEW IF EXISTS metric_p90_miss")
    op.execute("DROP VIEW IF EXISTS metric_overrun")
    op.execute("DROP VIEW IF EXISTS metric_pivot_rate")
    op.execute("DROP VIEW IF EXISTS metric_eur_per_hour")
    op.execute("DROP VIEW IF EXISTS metric_week_summary")
    op.execute("DROP FUNCTION IF EXISTS metric_utilization(integer)")

    op.execute(
        """
        CREATE FUNCTION metric_summary(p_start date, p_end date)
        RETURNS TABLE (
            visit_count integer,
            groomed_minutes integer,
            revenue_ex_tip numeric,
            revenue_inc_tip numeric,
            eur_per_hour_n integer,
            eur_per_hour_ex_tip numeric,
            eur_per_hour_inc_tip numeric
        )
        LANGUAGE sql
        STABLE
        AS $$
            WITH totals AS (
                SELECT
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
                WHERE (status IS NULL OR status = 'completed')
                  AND visit_date >= p_start
                  AND visit_date <= p_end
            ),
            eur AS (
                SELECT
                    COUNT(*)::int AS eur_per_hour_n,
                    CASE
                        WHEN COUNT(*) >= (SELECT min_n FROM metric_constants) THEN
                            (SUM(final_price) / (SUM(actual_minutes) / 60.0))::numeric
                        ELSE NULL
                    END AS eur_per_hour_ex_tip,
                    CASE
                        WHEN COUNT(*) >= (SELECT min_n FROM metric_constants) THEN
                            (SUM(final_price + COALESCE(tip, 0))
                             / (SUM(actual_minutes) / 60.0))::numeric
                        ELSE NULL
                    END AS eur_per_hour_inc_tip
                FROM visit
                WHERE (status IS NULL OR status = 'completed')
                  AND final_price IS NOT NULL
                  AND actual_minutes IS NOT NULL
                  AND actual_minutes > 0
                  AND visit_date >= p_start
                  AND visit_date <= p_end
            )
            SELECT
                t.visit_count,
                t.groomed_minutes,
                t.revenue_ex_tip,
                t.revenue_inc_tip,
                COALESCE(e.eur_per_hour_n, 0)::int,
                e.eur_per_hour_ex_tip,
                e.eur_per_hour_inc_tip
            FROM totals t
            CROSS JOIN eur e
            WHERE t.visit_count > 0
        $$
        """
    )

    op.execute(
        """
        CREATE FUNCTION metric_eur_per_hour(p_start date, p_end date)
        RETURNS TABLE (
            condition_score integer,
            shaved_down boolean,
            n integer,
            groomed_minutes integer,
            hours numeric,
            revenue_ex_tip numeric,
            revenue_inc_tip numeric,
            eur_per_hour_ex_tip numeric,
            eur_per_hour_inc_tip numeric
        )
        LANGUAGE sql
        STABLE
        AS $$
            SELECT
                v.condition_score,
                v.shaved_down,
                COUNT(*)::int AS n,
                COALESCE(SUM(v.actual_minutes), 0)::int AS groomed_minutes,
                (COALESCE(SUM(v.actual_minutes), 0) / 60.0)::numeric AS hours,
                COALESCE(SUM(v.final_price), 0)::numeric AS revenue_ex_tip,
                COALESCE(
                    SUM(v.final_price + COALESCE(v.tip, 0)),
                    0
                )::numeric AS revenue_inc_tip,
                CASE
                    WHEN COUNT(*) >= (SELECT min_n FROM metric_constants) THEN
                        (SUM(v.final_price) / (SUM(v.actual_minutes) / 60.0))::numeric
                    ELSE NULL
                END AS eur_per_hour_ex_tip,
                CASE
                    WHEN COUNT(*) >= (SELECT min_n FROM metric_constants) THEN
                        (SUM(v.final_price + COALESCE(v.tip, 0))
                         / (SUM(v.actual_minutes) / 60.0))::numeric
                    ELSE NULL
                END AS eur_per_hour_inc_tip
            FROM visit v
            WHERE (v.status IS NULL OR v.status = 'completed')
              AND v.final_price IS NOT NULL
              AND v.actual_minutes IS NOT NULL
              AND v.actual_minutes > 0
              AND v.condition_score IS NOT NULL
              AND v.shaved_down IS NOT NULL
              AND v.visit_date >= p_start
              AND v.visit_date <= p_end
            GROUP BY v.condition_score, v.shaved_down
            ORDER BY v.condition_score, v.shaved_down
        $$
        """
    )

    op.execute(
        """
        CREATE FUNCTION metric_pivot_rate(p_start date, p_end date)
        RETURNS TABLE (
            n integer,
            pivoted_count integer,
            pivot_rate numeric
        )
        LANGUAGE sql
        STABLE
        AS $$
            SELECT
                COUNT(*)::int AS n,
                COUNT(*) FILTER (WHERE pivoted IS TRUE)::int AS pivoted_count,
                CASE
                    WHEN COUNT(*) >= (SELECT min_n FROM metric_constants) THEN
                        (COUNT(*) FILTER (WHERE pivoted IS TRUE)::numeric / COUNT(*))
                    ELSE NULL
                END AS pivot_rate
            FROM visit
            WHERE (status IS NULL OR status = 'completed')
              AND visit_date >= p_start
              AND visit_date <= p_end
        $$
        """
    )

    op.execute(
        """
        CREATE FUNCTION metric_overrun(p_start date, p_end date)
        RETURNS TABLE (
            n integer,
            avg_overrun_minutes numeric
        )
        LANGUAGE sql
        STABLE
        AS $$
            SELECT
                COUNT(*)::int AS n,
                CASE
                    WHEN COUNT(*) >= (SELECT min_n FROM metric_constants) THEN
                        AVG(actual_minutes - predicted_min_p50)::numeric
                    ELSE NULL
                END AS avg_overrun_minutes
            FROM visit
            WHERE (status IS NULL OR status = 'completed')
              AND predicted_min_p50 IS NOT NULL
              AND actual_minutes IS NOT NULL
              AND visit_date >= p_start
              AND visit_date <= p_end
        $$
        """
    )

    op.execute(
        """
        CREATE FUNCTION metric_p90_miss(p_start date, p_end date)
        RETURNS TABLE (
            n integer,
            miss_count integer,
            miss_rate numeric
        )
        LANGUAGE sql
        STABLE
        AS $$
            SELECT
                COUNT(*)::int AS n,
                COUNT(*) FILTER (
                    WHERE actual_minutes > predicted_min_p90
                )::int AS miss_count,
                CASE
                    WHEN COUNT(*) >= (SELECT min_n FROM metric_constants) THEN
                        (COUNT(*) FILTER (
                            WHERE actual_minutes > predicted_min_p90
                        )::numeric / COUNT(*))
                    ELSE NULL
                END AS miss_rate
            FROM visit
            WHERE (status IS NULL OR status = 'completed')
              AND predicted_min_p90 IS NOT NULL
              AND actual_minutes IS NOT NULL
              AND visit_date >= p_start
              AND visit_date <= p_end
        $$
        """
    )

    op.execute(
        """
        CREATE FUNCTION metric_utilization(
            buffer_minutes integer,
            p_start date,
            p_end date
        )
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
            WHERE (v.status IS NULL OR v.status = 'completed')
              AND v.visit_date >= p_start
              AND v.visit_date <= p_end
            GROUP BY v.visit_date
            ORDER BY v.visit_date
        $$
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS metric_utilization(integer, date, date)")
    op.execute("DROP FUNCTION IF EXISTS metric_p90_miss(date, date)")
    op.execute("DROP FUNCTION IF EXISTS metric_overrun(date, date)")
    op.execute("DROP FUNCTION IF EXISTS metric_pivot_rate(date, date)")
    op.execute("DROP FUNCTION IF EXISTS metric_eur_per_hour(date, date)")
    op.execute("DROP FUNCTION IF EXISTS metric_summary(date, date)")

    # Restore pre-#170 objects (state after a1b2c3d4e5f6).
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
