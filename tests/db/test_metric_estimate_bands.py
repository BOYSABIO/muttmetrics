"""metric_estimate_bands(start, end) vs hand-computed EXPECTED (2026-11-14)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session
from tests.fixtures.metric_week import EXPECTED, WEEK_END, WEEK_START


def _bands(session: Session, start: date, end: date) -> dict:
    return dict(
        session.execute(text("SELECT * FROM metric_estimate_bands(:s, :e)"), {"s": start, "e": end})
        .mappings()
        .one()
    )


def test_bands_match_the_hand_math(db_session: Session, metric_week: dict) -> None:
    row = _bands(db_session, WEEK_START, WEEK_END)
    assert row == EXPECTED["estimate_bands"]
    # Same visits as the P90 miss rate, so the two can never disagree
    assert row["n"] == EXPECTED["p90_miss"]["n"]
    assert row["past_p90"] == EXPECTED["p90_miss"]["miss_count"]
    assert row["within_p50"] + row["within_p90"] + row["past_p90"] == row["n"]


def test_empty_range_is_zero_and_not_enough(db_session: Session) -> None:
    row = _bands(db_session, date(2025, 1, 6), date(2025, 1, 12))
    assert row == {"n": 0, "within_p50": 0, "within_p90": 0, "past_p90": 0, "enough": False}
