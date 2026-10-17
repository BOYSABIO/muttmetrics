"""Timing checks (pivot, overrun, P90 miss) vs Syn* EXPECTED (#28 / #170)."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from tests.fixtures.metric_week import EXPECTED, WEEK_END, WEEK_START


def test_pivot_overrun_p90_week_matches_fixture(db_session: Session, metric_week: dict) -> None:
    params = {"p_start": WEEK_START, "p_end": WEEK_END}

    pivot = (
        db_session.execute(
            text(
                """
                SELECT n, pivoted_count, pivot_rate
                FROM metric_pivot_rate(:p_start, :p_end)
                """
            ),
            params,
        )
        .mappings()
        .one()
    )
    exp_p = EXPECTED["pivot"]
    assert pivot["n"] == exp_p["n"]
    assert pivot["pivoted_count"] == exp_p["pivoted_count"]
    assert float(pivot["pivot_rate"]) == pytest.approx(exp_p["rate"])

    overrun = (
        db_session.execute(
            text(
                """
                SELECT n, avg_overrun_minutes
                FROM metric_overrun(:p_start, :p_end)
                """
            ),
            params,
        )
        .mappings()
        .one()
    )
    exp_o = EXPECTED["overrun"]
    assert overrun["n"] == exp_o["n"]
    assert float(overrun["avg_overrun_minutes"]) == pytest.approx(exp_o["avg_minutes"])

    p90 = (
        db_session.execute(
            text(
                """
                SELECT n, miss_count, miss_rate
                FROM metric_p90_miss(:p_start, :p_end)
                """
            ),
            params,
        )
        .mappings()
        .one()
    )
    exp_m = EXPECTED["p90_miss"]
    assert p90["n"] == exp_m["n"]
    assert p90["miss_count"] == exp_m["miss_count"]
    assert float(p90["miss_rate"]) == pytest.approx(exp_m["rate"])
