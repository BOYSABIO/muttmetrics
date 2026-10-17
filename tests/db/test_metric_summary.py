"""metric_summary(start, end) vs hand-computed EXPECTED (#170 range)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from tests.fixtures.metric_week import EXPECTED, WEEK_END, WEEK_START


def test_metric_summary_week_matches_fixture(db_session: Session, metric_week: dict) -> None:
    rows = (
        db_session.execute(
            text(
                """
            SELECT visit_count, groomed_minutes,
                revenue_ex_tip, revenue_inc_tip,
                eur_per_hour_n, eur_per_hour_ex_tip, eur_per_hour_inc_tip
            FROM metric_summary(:p_start, :p_end)
            """
            ),
            {"p_start": WEEK_START, "p_end": WEEK_END},
        )
        .mappings()
        .all()
    )

    assert len(rows) == 1
    row = rows[0]
    expected = EXPECTED["week_summary"][date(2026, 3, 2)]

    assert row["visit_count"] == expected["visit_count"]
    assert row["groomed_minutes"] == expected["groomed_minutes"]
    assert float(row["revenue_ex_tip"]) == pytest.approx(expected["revenue_ex_tip"])
    assert float(row["revenue_inc_tip"]) == pytest.approx(expected["revenue_inc_tip"])
    assert row["eur_per_hour_n"] == expected["eur_per_hour_n"]
    assert float(row["eur_per_hour_ex_tip"]) == pytest.approx(expected["eur_per_hour_ex_tip"])
    assert float(row["eur_per_hour_inc_tip"]) == pytest.approx(expected["eur_per_hour_inc_tip"])


def test_metric_summary_empty_range_returns_no_row(db_session: Session, metric_week: dict) -> None:
    empty_start = WEEK_START + timedelta(days=14)
    rows = (
        db_session.execute(
            text("SELECT * FROM metric_summary(:p_start, :p_end)"),
            {"p_start": empty_start, "p_end": empty_start + timedelta(days=6)},
        )
        .mappings()
        .all()
    )
    assert rows == []
