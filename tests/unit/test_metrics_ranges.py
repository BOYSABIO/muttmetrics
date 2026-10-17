"""Pure date logic behind /metrics/period (#170, tests added in #180)."""

from datetime import date

import pytest

from muttmetrics.api.services.metrics import classify_period, previous_range


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
