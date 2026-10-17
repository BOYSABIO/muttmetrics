"""metric_utilization(_weeks)(buffer, start, end) vs Syn* EXPECTED (#29 / #170 / #178)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session
from tests.fixtures.metric_month import BUFFER_MINUTES as MONTH_BUFFER
from tests.fixtures.metric_month import EXPECTED as MONTH_EXPECTED
from tests.fixtures.metric_month import MONTH_END, MONTH_START
from tests.fixtures.metric_week import BUFFER_MINUTES, EXPECTED, WEEK_END, WEEK_START


def test_utilization_over_under_and_missing_prediction(
    db_session: Session, metric_week: dict
) -> None:
    rows = (
        db_session.execute(
            text(
                """
                SELECT * FROM metric_utilization(:buffer, :p_start, :p_end)
                ORDER BY visit_date
                """
            ),
            {
                "buffer": BUFFER_MINUTES,
                "p_start": WEEK_START,
                "p_end": WEEK_END,
            },
        )
        .mappings()
        .all()
    )

    by_day = {r["visit_date"]: r for r in rows}

    mon = by_day[date(2026, 3, 2)]
    exp_mon = EXPECTED["utilization"][date(2026, 3, 2)]
    assert mon["n"] == exp_mon["n"]
    assert mon["planned_p50"] == exp_mon["planned_p50"]
    assert mon["planned_p90"] == exp_mon["planned_p90"]
    assert mon["actual_minutes"] == exp_mon["actual_minutes"]
    assert mon["missing_prediction"] == exp_mon["missing_prediction"]
    assert mon["over_buffer"] is False

    tue = by_day[date(2026, 3, 3)]
    exp_tue = EXPECTED["utilization"][date(2026, 3, 3)]
    assert tue["n"] == exp_tue["n"]
    assert tue["planned_p90"] == exp_tue["planned_p90"] == 350
    assert tue["over_buffer"] is True

    fri = by_day[date(2026, 3, 6)]
    exp_fri = EXPECTED["utilization"][date(2026, 3, 6)]
    assert fri["n"] == exp_fri["n"]
    assert fri["planned_p50"] == exp_fri["planned_p50"] == 50
    assert fri["planned_p90"] == exp_fri["planned_p90"] == 70
    assert fri["actual_minutes"] == exp_fri["actual_minutes"] == 100
    assert fri["missing_prediction"] == exp_fri["missing_prediction"] == 1
    assert fri["over_buffer"] is False

    assert date(2026, 3, 7) not in by_day


# --- #178: weekly rollup, defined on top of the per-day function -------------

_WEEKS_SQL = text(
    """
    SELECT * FROM metric_utilization_weeks(:buffer, :p_start, :p_end)
    ORDER BY week_start
    """
)


def test_utilization_weeks_sums_days_and_counts_over_days(
    db_session: Session, metric_week: dict
) -> None:
    rows = (
        db_session.execute(
            _WEEKS_SQL,
            {"buffer": BUFFER_MINUTES, "p_start": WEEK_START, "p_end": WEEK_END},
        )
        .mappings()
        .all()
    )
    assert len(rows) == 1
    expected = EXPECTED["utilization_weeks"][WEEK_START]
    assert rows[0]["week_start"] == WEEK_START
    for key, value in expected.items():
        assert rows[0][key] == value, key


def test_utilization_weeks_clips_edge_weeks_to_the_month(
    db_session: Session, metric_month: dict
) -> None:
    rows = (
        db_session.execute(
            _WEEKS_SQL,
            {"buffer": MONTH_BUFFER, "p_start": MONTH_START, "p_end": MONTH_END},
        )
        .mappings()
        .all()
    )
    by_week = {r["week_start"]: r for r in rows}
    assert set(by_week) == set(MONTH_EXPECTED["utilization_weeks"])
    for week_start, bounds in MONTH_EXPECTED["utilization_weeks"].items():
        row = by_week[week_start]
        assert row["range_start"] == bounds["range_start"]
        assert row["range_end"] == bounds["range_end"]
        for key, value in MONTH_EXPECTED["utilization_week_totals"].items():
            assert row[key] == value, (week_start, key)
