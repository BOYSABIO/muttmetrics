"""Month range vs SynMonth* EXPECTED — weeks thin, month unlocks (#170)."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from tests.fixtures.metric_month import (
    EXPECTED,
    LEAK_DATE,
    MIN_N,
    MONTH_END,
    MONTH_START,
)


def test_month_summary_above_min_n_while_weeks_thin(
    db_session: Session, metric_month: dict
) -> None:
    row = (
        db_session.execute(
            text(
                """
                SELECT visit_count, groomed_minutes, revenue_ex_tip, revenue_inc_tip,
                       eur_per_hour_n, eur_per_hour_ex_tip, eur_per_hour_inc_tip
                FROM metric_summary(:p_start, :p_end)
                """
            ),
            {"p_start": MONTH_START, "p_end": MONTH_END},
        )
        .mappings()
        .one()
    )
    exp = EXPECTED["summary"]
    assert row["visit_count"] == exp["visit_count"]
    assert row["groomed_minutes"] == exp["groomed_minutes"]
    assert float(row["revenue_ex_tip"]) == pytest.approx(exp["revenue_ex_tip"])
    assert float(row["revenue_inc_tip"]) == pytest.approx(exp["revenue_inc_tip"])
    assert row["eur_per_hour_n"] == exp["eur_per_hour_n"] >= MIN_N
    assert float(row["eur_per_hour_ex_tip"]) == pytest.approx(exp["eur_per_hour_ex_tip"])
    assert float(row["eur_per_hour_inc_tip"]) == pytest.approx(exp["eur_per_hour_inc_tip"])

    thin = EXPECTED["thin_week"]
    thin_row = (
        db_session.execute(
            text(
                """
                SELECT visit_count, eur_per_hour_n, eur_per_hour_ex_tip
                FROM metric_summary(:p_start, :p_end)
                """
            ),
            {"p_start": thin["start"], "p_end": thin["end"]},
        )
        .mappings()
        .one()
    )
    assert thin_row["visit_count"] == thin["visit_count"]
    assert thin_row["eur_per_hour_n"] == thin["eur_per_hour_n"] < MIN_N
    assert thin_row["eur_per_hour_ex_tip"] is None


def test_month_range_excludes_prior_day_includes_first(
    db_session: Session, metric_month: dict
) -> None:
    """Mar 31 must not leak; Apr 1 must count."""
    april = (
        db_session.execute(
            text("SELECT visit_count FROM metric_summary(:p_start, :p_end)"),
            {"p_start": MONTH_START, "p_end": MONTH_END},
        )
        .mappings()
        .one()
    )
    march_only = (
        db_session.execute(
            text("SELECT visit_count FROM metric_summary(:p_start, :p_end)"),
            {"p_start": LEAK_DATE, "p_end": LEAK_DATE},
        )
        .mappings()
        .one()
    )
    assert april["visit_count"] == EXPECTED["summary"]["visit_count"]
    assert march_only["visit_count"] == 1

    first_day = (
        db_session.execute(
            text("SELECT visit_count FROM metric_summary(:p_start, :p_end)"),
            {"p_start": MONTH_START, "p_end": MONTH_START},
        )
        .mappings()
        .one()
    )
    assert first_day["visit_count"] == 1


def test_iso_week_buckets_each_below_min_n(db_session: Session, metric_month: dict) -> None:
    from datetime import timedelta

    for week_monday, n in EXPECTED["iso_week_buckets"].items():
        sun = week_monday + timedelta(days=6)
        clipped_start = max(week_monday, MONTH_START)
        clipped_end = min(sun, MONTH_END)
        row = (
            db_session.execute(
                text("SELECT visit_count FROM metric_summary(:p_start, :p_end)"),
                {"p_start": clipped_start, "p_end": clipped_end},
            )
            .mappings()
            .one()
        )
        assert row["visit_count"] == n < MIN_N
