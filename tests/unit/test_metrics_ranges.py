"""Pure date logic behind /metrics/period (#170, tests added in #180)."""

from datetime import date

import pytest

from muttmetrics.api.services.metrics import (
    RECENT_DAYS,
    classify_period,
    comparison_range,
    previous_range,
    recent_range,
)


@pytest.mark.parametrize(
    ("start", "end", "kind"),
    [
        (date(2026, 3, 2), date(2026, 3, 8), "week"),  # Mon..Sun
        (date(2026, 3, 3), date(2026, 3, 9), "custom"),  # 7 days, not Monday
        (date(2026, 2, 1), date(2026, 2, 28), "month"),
        (date(2028, 2, 1), date(2028, 2, 29), "month"),  # leap year
        (date(2026, 2, 1), date(2026, 2, 27), "custom"),
    ],
)
def test_classify_period(start: date, end: date, kind: str) -> None:
    assert classify_period(start, end) == kind


@pytest.mark.parametrize(
    ("start", "end", "kind", "expected"),
    [
        (date(2026, 1, 1), date(2026, 1, 31), "month", (date(2025, 12, 1), date(2025, 12, 31))),
        (date(2026, 3, 1), date(2026, 3, 31), "month", (date(2026, 2, 1), date(2026, 2, 28))),
        (date(2026, 3, 2), date(2026, 3, 8), "week", (date(2026, 2, 23), date(2026, 3, 1))),
        (date(2026, 3, 3), date(2026, 3, 5), "custom", (date(2026, 2, 28), date(2026, 3, 2))),
    ],
)
def test_previous_range(start: date, end: date, kind: str, expected: tuple[date, date]) -> None:
    assert previous_range(start, end, kind) == expected


# --- 0.6.5: fair comparison while a period is running, and the recent window ---


def test_running_week_is_compared_with_the_same_days_of_last_week() -> None:
    # Tuesday Nov 10: this week so far is Mon-Tue, so last week is Mon-Tue too.
    assert comparison_range(date(2026, 11, 9), date(2026, 11, 15), "week", date(2026, 11, 10)) == (
        date(2026, 11, 2),
        date(2026, 11, 3),
        True,
    )


def test_monday_compares_one_day_with_one_day() -> None:
    assert comparison_range(date(2026, 11, 9), date(2026, 11, 15), "week", date(2026, 11, 9)) == (
        date(2026, 11, 2),
        date(2026, 11, 2),
        True,
    )


def test_finished_period_compares_whole_ranges() -> None:
    # Sunday (the last day) and any later day: the whole previous week.
    for today in (date(2026, 11, 15), date(2026, 12, 1)):
        assert comparison_range(date(2026, 11, 9), date(2026, 11, 15), "week", today) == (
            date(2026, 11, 2),
            date(2026, 11, 8),
            False,
        )


def test_running_month_is_clipped_but_never_past_a_short_previous_month() -> None:
    # Mar 30: 29 days elapsed, February only has 28, so it stops at Feb 28.
    assert comparison_range(date(2026, 3, 1), date(2026, 3, 31), "month", date(2026, 3, 30)) == (
        date(2026, 2, 1),
        date(2026, 2, 28),
        True,
    )
    assert comparison_range(date(2026, 3, 1), date(2026, 3, 31), "month", date(2026, 3, 10)) == (
        date(2026, 2, 1),
        date(2026, 2, 10),
        True,
    )


def test_recent_window_ends_at_the_period_end_or_today() -> None:
    assert RECENT_DAYS == 90
    # A past week: the 90 days up to its Sunday.
    assert recent_range(date(2026, 4, 5), date(2026, 11, 8)) == (
        date(2026, 1, 6),
        date(2026, 4, 5),
    )
    # The running week: up to today, not into the future.
    start, end = recent_range(date(2026, 11, 15), date(2026, 11, 10))
    assert end == date(2026, 11, 10)
    assert (end - start).days + 1 == RECENT_DAYS
