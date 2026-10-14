"""metric_week_summary view vs hand-computed EXPECTED."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from tests.fixtures.metric_week import EXPECTED, WEEK_START


def test_metric_week_summary_matches_fixture(db_session: Session, metric_week: dict) -> None:
    rows = (
        db_session.execute(
            text(
                """
            SELECT week_start, visit_count, groomed_minutes,
                revenue_ex_tip, revenue_inc_tip
            FROM metric_week_summary
            WHERE week_start = :week_start
            """
            ),
            {"week_start": WEEK_START},
        )
        .mappings()
        .all()
    )

    # Filter to Syn* week only - real DB may have other weeks committed
    assert len(rows) == 1
    row = rows[0]
    expected = EXPECTED["week_summary"][date(2026, 3, 2)]

    assert row["visit_count"] == expected["visit_count"]
    assert row["groomed_minutes"] == expected["groomed_minutes"]
    assert float(row["revenue_ex_tip"]) == pytest.approx(expected["revenue_ex_tip"])
    assert float(row["revenue_inc_tip"]) == pytest.approx(expected["revenue_inc_tip"])
