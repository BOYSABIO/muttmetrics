"""fixed_cost table + metric_rent(): "is the rent covered?" (2026-11, #229)

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-11-25

fixed_cost (new): one row per change of a monthly cost. Only 'rent' for now
(utilities included in it); other kinds come with #59. A row says "from this
month on, it's this much", so a rent change later never rewrites old months.
The amounts are the salon's own figures: they live in the database only,
set on the box with ops/rent.py, never in the repo.

metric_rent(p_start, p_end) (new, ADR-003 range function): one row per
calendar month touching the range, with that month's rent (NULL before the
first rent row), its take-home (completed visits, price + tip, the same rule
as metric_summary's revenue_inc_tip) and the first day the take-home reached
the rent (NULL while it hasn't). Rent is due on the 1st, so a month counts in
full from its first day.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: str | Sequence[str] | None = "d0e1f2a3b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fixed_cost",
        sa.Column("fixed_cost_id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("monthly_amount", sa.Numeric(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("kind IN ('rent')", name="ck_fixed_cost_kind"),
        sa.CheckConstraint("monthly_amount >= 0", name="ck_fixed_cost_amount"),
        sa.CheckConstraint("EXTRACT(DAY FROM valid_from) = 1", name="ck_fixed_cost_first_of_month"),
        sa.UniqueConstraint("kind", "valid_from", name="uq_fixed_cost_kind_valid_from"),
    )

    op.execute(
        """
        CREATE FUNCTION metric_rent(p_start date, p_end date)
        RETURNS TABLE (
            month_start date,
            rent numeric,
            take_home numeric,
            covered_on date
        )
        LANGUAGE sql
        STABLE
        AS $$
            WITH months AS (
                SELECT gs::date AS m
                FROM generate_series(
                    date_trunc('month', p_start::timestamp),
                    date_trunc('month', p_end::timestamp),
                    interval '1 month'
                ) AS gs
            ),
            rent_by_month AS (
                SELECT
                    months.m,
                    (
                        SELECT fc.monthly_amount
                        FROM fixed_cost fc
                        WHERE fc.kind = 'rent' AND fc.valid_from <= months.m
                        ORDER BY fc.valid_from DESC
                        LIMIT 1
                    ) AS amount
                FROM months
            ),
            days AS (
                SELECT
                    date_trunc('month', v.visit_date::timestamp)::date AS m,
                    v.visit_date AS d,
                    SUM(v.final_price + COALESCE(v.tip, 0)) AS amount
                FROM visit v
                WHERE (v.status IS NULL OR v.status = 'completed')
                  AND v.final_price IS NOT NULL
                  AND v.visit_date >= date_trunc('month', p_start::timestamp)::date
                  AND v.visit_date < (date_trunc('month', p_end::timestamp)
                                      + interval '1 month')::date
                GROUP BY 1, 2
            ),
            running AS (
                SELECT m, d, SUM(amount) OVER (PARTITION BY m ORDER BY d) AS so_far
                FROM days
            )
            SELECT
                r.m,
                r.amount,
                COALESCE((SELECT SUM(days.amount) FROM days WHERE days.m = r.m), 0)::numeric,
                (
                    SELECT MIN(running.d)
                    FROM running
                    WHERE running.m = r.m
                      AND r.amount IS NOT NULL
                      AND running.so_far >= r.amount
                )
            FROM rent_by_month r
            ORDER BY r.m
        $$
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS metric_rent(date, date)")
    op.drop_table("fixed_cost")
