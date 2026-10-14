"""metric_utilization(buffer) vs Syn* EXPECTED (#29)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session
from tests.fixtures.metric_week import BUFFER_MINUTES, EXPECTED


def test_utilization_over_under_and_missing_prediction(
    db_session: Session, metric_week: dict
) -> None:
    rows = (
        db_session.execute(
            text("SELECT * FROM metric_utilization(:buffer) ORDER BY visit_date"),
            {"buffer": BUFFER_MINUTES},
        )
        .mappings()
        .all()
    )

    by_day = {r["visit_date"]: r for r in rows}

    # Mon — under buffer
    mon = by_day[date(2026, 3, 2)]
    exp_mon = EXPECTED["utilization"][date(2026, 3, 2)]
    assert mon["n"] == exp_mon["n"]
    assert mon["planned_p50"] == exp_mon["planned_p50"]
    assert mon["planned_p90"] == exp_mon["planned_p90"]
    assert mon["actual_minutes"] == exp_mon["actual_minutes"]
    assert mon["missing_prediction"] == exp_mon["missing_prediction"]
    assert mon["over_buffer"] is False

    # Tue — over buffer (P90 sum 350 > 240)
    tue = by_day[date(2026, 3, 3)]
    exp_tue = EXPECTED["utilization"][date(2026, 3, 3)]
    assert tue["n"] == exp_tue["n"]
    assert tue["planned_p90"] == exp_tue["planned_p90"] == 350
    assert tue["over_buffer"] is True

    # Fri — V8 has no P50; still counts in n / actual, not as 0 planned
    fri = by_day[date(2026, 3, 6)]
    exp_fri = EXPECTED["utilization"][date(2026, 3, 6)]
    assert fri["n"] == exp_fri["n"]
    assert fri["planned_p50"] == exp_fri["planned_p50"] == 50
    assert fri["planned_p90"] == exp_fri["planned_p90"] == 70
    assert fri["actual_minutes"] == exp_fri["actual_minutes"] == 100
    assert fri["missing_prediction"] == exp_fri["missing_prediction"] == 1
    assert fri["over_buffer"] is False

    # Sat only no_show → no eligible row
    assert date(2026, 3, 7) not in by_day
