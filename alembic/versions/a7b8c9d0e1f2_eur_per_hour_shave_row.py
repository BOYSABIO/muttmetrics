"""metric_eur_per_hour: shave-downs as one row (2026-11-14)

Revision ID: a7b8c9d0e1f2
Revises: f3a4b5c6d7e8
Create Date: 2026-11-14

#27 grouped € / hour by coat condition (0–5) x shaved_down: up to 12 cells,
each needing MIN_N grooms. Shave-downs happen almost only on bad coats, so most
"x shaved" cells could never fill, and "Coat 1" next to "Coat 1 · shaved" read
as two kinds of coat. Now every shave-down is one cell (condition_score NULL,
shaved_down true), whatever the condition was; every other visit stays in its
condition cell. 7 cells instead of 12. A visit with shaved_down NULL counts as
not shaved. Same return type, so CREATE OR REPLACE; no table changes.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: str | Sequence[str] | None = "f3a4b5c6d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_SQL = """
        CREATE OR REPLACE FUNCTION metric_eur_per_hour(p_start date, p_end date)
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
                -- Shave-downs are one row whatever the coat's condition was;
                -- every other visit is grouped by its condition (0 worst … 5 best).
                CASE WHEN v.shaved_down IS TRUE THEN NULL ELSE v.condition_score END
                    AS condition_score,
                COALESCE(v.shaved_down, false) AS shaved_down,
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
              AND (v.shaved_down IS TRUE OR v.condition_score IS NOT NULL)
              AND v.visit_date >= p_start
              AND v.visit_date <= p_end
            GROUP BY 1, 2
            ORDER BY 2, 1
        $$
"""

# The #170 definition, restored on downgrade.
DOWNGRADE_SQL = """
        CREATE OR REPLACE FUNCTION metric_eur_per_hour(p_start date, p_end date)
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


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
