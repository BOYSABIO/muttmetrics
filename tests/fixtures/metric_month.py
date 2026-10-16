"""SYNTHETIC metric-month dataset with hand-computed EXPECTED (#170).

Not real client data. Names are deliberately fake (SynMonth*).

Why this month exists: every ISO-week slice inside April has n < MIN_N,
but the calendar month total is above MIN_N — so week views stay "Not yet"
while the month shows real averages. That is the product reason for #170.

Calendar month: 2026-04-01 → 2026-04-30.
ISO weeks touched (visit_date buckets):
  Mon 2026-03-30: Apr 1–2 visits (n=2 in month; Mar 31 is OUTSIDE)
  Mon 2026-04-06: Apr 8–9 (n=2)
  Mon 2026-04-13: Apr 15–16 (n=2)
Leak control: SynMonth visit on 2026-03-31 must not appear in April range.
"""

from __future__ import annotations

from datetime import date
from typing import Any, TypedDict

from tests.fixtures.metric_week import MIN_N

BUFFER_MINUTES = 240

MONTH_START = date(2026, 4, 1)
MONTH_END = date(2026, 4, 30)
# Immediately before the month — must not leak into April metrics.
LEAK_DATE = date(2026, 3, 31)


class VisitSpec(TypedDict):
    key: str
    dog_key: str
    visit_date: date
    status: str | None
    condition_score: int | None
    shaved_down: bool | None
    pivoted: bool | None
    actual_minutes: int
    predicted_min_p50: int | None
    predicted_min_p90: int | None
    final_price: float | None
    tip: float | None
    note: str


OWNERS: list[dict[str, str]] = [
    {"key": "m", "name": "SynMonth Owner"},
]

DOGS: list[dict[str, str]] = [
    {
        "key": "month",
        "name": "SynMonth Dog",
        "owner_key": "m",
        "breed_en": "SynMonth Breed",
    },
]


def _visit(
    key: str,
    visit_date: date,
    *,
    note: str,
    status: str | None = "completed",
    minutes: int = 60,
    price: float | None = 60.0,
    tip: float | None = 0.0,
    p50: int | None = 55,
    p90: int | None = 75,
) -> VisitSpec:
    return {
        "key": key,
        "dog_key": "month",
        "visit_date": visit_date,
        "status": status,
        "condition_score": 0,
        "shaved_down": True,
        "pivoted": False,
        "actual_minutes": minutes,
        "predicted_min_p50": p50,
        "predicted_min_p90": p90,
        "final_price": price,
        "tip": tip,
        "note": note,
    }


# fmt: off
VISITS: list[VisitSpec] = [
    _visit("ML", LEAK_DATE, note="Mar 31 leak — outside April"),
    _visit("M1", date(2026, 4, 1), note="Apr 1 first day; week Mar 30"),
    _visit("M2", date(2026, 4, 2), note="same ISO week as M1"),
    _visit("M3", date(2026, 4, 8), note="week Apr 6"),
    _visit("M4", date(2026, 4, 9), note="week Apr 6"),
    _visit("M5", date(2026, 4, 15), note="week Apr 13"),
    _visit("M6", date(2026, 4, 16), note="week Apr 13"),
    _visit(
        "MX",
        date(2026, 4, 20),
        note="cancelled — excluded from all metrics",
        status="cancelled",
        minutes=60,
        price=60.0,
    ),
]
# fmt: on

# Hand math — April eligible only (M1–M6; not ML, not MX)
#   n = 6, minutes = 360, rev ex = 360, rev inc = 360
#   eur hours = 6.0 → €/hour = 60.0 (6 >= MIN_N → show)
_MONTH_EUR_N = 6
_MONTH_EUR_EX = 60.0
_MONTH_EUR_INC = 60.0

# ISO week Apr 6–12 alone (M3, M4): n=2 < MIN_N → rates NULL
_THIN_WEEK_START = date(2026, 4, 6)
_THIN_WEEK_END = date(2026, 4, 12)

EXPECTED: dict[str, Any] = {
    "min_n": MIN_N,
    "month": {"start": MONTH_START, "end": MONTH_END},
    "leak_date": LEAK_DATE,
    "summary": {
        "visit_count": 6,
        "groomed_minutes": 360,
        "revenue_ex_tip": 360.0,
        "revenue_inc_tip": 360.0,
        "eur_per_hour_n": _MONTH_EUR_N,
        "eur_per_hour_ex_tip": _MONTH_EUR_EX,
        "eur_per_hour_inc_tip": _MONTH_EUR_INC,
        "show_eur_rate": True,
    },
    # Each ISO-week bucket inside the month is below MIN_N
    "iso_week_buckets": {
        date(2026, 3, 30): 2,  # M1, M2
        date(2026, 4, 6): 2,  # M3, M4
        date(2026, 4, 13): 2,  # M5, M6
    },
    "thin_week": {
        "start": _THIN_WEEK_START,
        "end": _THIN_WEEK_END,
        "visit_count": 2,
        "eur_per_hour_n": 2,
        "show_eur_rate": False,
    },
    "eur_per_hour": {
        (0, True): {
            "n": 6,
            "show_rate": True,
            "eur_per_hour_ex_tip": 60.0,
            "eur_per_hour_inc_tip": 60.0,
            "revenue_ex_tip": 360.0,
            "revenue_inc_tip": 360.0,
            "hours": 6.0,
        },
    },
}
