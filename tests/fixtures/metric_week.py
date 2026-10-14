"""SYNTHETIC metric-week dataset with hand-computed EXPECTED (#16).

Not real client data. Names are deliberately fake (Syn*). Definitions:
``docs/runbooks/analytics.md``.

Week under test: Mon 2026-03-02 → Sun 2026-03-08.
Empty week (no rows): Mon 2026-03-09 → Sun 2026-03-15.
Closing buffer for utilization: 240 minutes.
"""

from __future__ import annotations

from datetime import date
from typing import Any, TypedDict

# Same constant as analytics runbook — single source for fixture expectations.
MIN_N = 5
BUFFER_MINUTES = 240

WEEK_START = date(2026, 3, 2)
WEEK_END = date(2026, 3, 8)
EMPTY_WEEK_START = date(2026, 3, 9)
EMPTY_WEEK_END = date(2026, 3, 15)


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
    {"key": "a", "name": "Syn Owner Alpha"},
    {"key": "b", "name": "Syn Owner Bravo"},
]

DOGS: list[dict[str, str]] = [
    {
        "key": "matted",
        "name": "SynDog Matted",
        "owner_key": "a",
        "breed_en": "Syn Breed Matted",
    },
    {
        "key": "fluff",
        "name": "SynDog Fluff",
        "owner_key": "a",
        "breed_en": "Syn Breed Fluff",
    },
    {
        "key": "mix",
        "name": "SynDog Mix",
        "owner_key": "b",
        "breed_en": "Syn Breed Mix",
    },
]

# fmt: off
VISITS: list[VisitSpec] = [
    # Mon 02 — thin cells (below MIN_N when alone)
    {
        "key": "V11", "dog_key": "fluff", "visit_date": date(2026, 3, 2),
        "status": "completed", "condition_score": 4, "shaved_down": False,
        "pivoted": False, "actual_minutes": 55, "predicted_min_p50": 50,
        "predicted_min_p90": 70, "final_price": 48.0, "tip": 5.0,
        "note": "cond 4 × not shaved; under-run vs P50",
    },
    {
        "key": "V12", "dog_key": "matted", "visit_date": date(2026, 3, 2),
        "status": "completed", "condition_score": 4, "shaved_down": True,
        "pivoted": False, "actual_minutes": 70, "predicted_min_p50": 60,
        "predicted_min_p90": 80, "final_price": 52.0, "tip": 0.0,
        "note": "cond 4 × shaved; alone → n=1 < MIN_N for €/hour",
    },
    # Tue 03 — busy day (after V15: sum P90 > buffer)
    {
        "key": "V1", "dog_key": "matted", "visit_date": date(2026, 3, 3),
        "status": "completed", "condition_score": 0, "shaved_down": True,
        "pivoted": False, "actual_minutes": 120, "predicted_min_p50": 90,
        "predicted_min_p90": 110, "final_price": 70.0, "tip": 15.0,
        "note": "matted+shaved; overruns P50 and P90; tip in 5–20",
    },
    {
        "key": "V2", "dog_key": "matted", "visit_date": date(2026, 3, 3),
        "status": "completed", "condition_score": 0, "shaved_down": True,
        "pivoted": False, "actual_minutes": 100, "predicted_min_p50": 90,
        "predicted_min_p90": 110, "final_price": 65.0, "tip": None,
        "note": "NULL tip → coalesce to 0 for inc-tip revenue",
    },
    {
        "key": "V15", "dog_key": "mix", "visit_date": date(2026, 3, 3),
        "status": "completed", "condition_score": 2, "shaved_down": False,
        "pivoted": False, "actual_minutes": 80, "predicted_min_p50": 100,
        "predicted_min_p90": 130, "final_price": 58.0, "tip": 10.0,
        "note": "pushes Tue sum(P90)=350 > buffer 240; under P50",
    },
    # Wed 04
    {
        "key": "V3", "dog_key": "matted", "visit_date": date(2026, 3, 4),
        "status": "completed", "condition_score": 0, "shaved_down": True,
        "pivoted": True, "actual_minutes": 95, "predicted_min_p50": 90,
        "predicted_min_p90": 110, "final_price": 60.0, "tip": 10.0,
        "note": "only pivoted visit in the week",
    },
    {
        "key": "V4", "dog_key": "matted", "visit_date": date(2026, 3, 4),
        "status": "completed", "condition_score": 0, "shaved_down": True,
        "pivoted": False, "actual_minutes": 90, "predicted_min_p50": 90,
        "predicted_min_p90": 110, "final_price": 60.0, "tip": 0.0,
        "note": "exact P50; explicit tip 0",
    },
    # Thu 05
    {
        "key": "V5", "dog_key": "matted", "visit_date": date(2026, 3, 5),
        "status": "completed", "condition_score": 0, "shaved_down": True,
        "pivoted": False, "actual_minutes": 85, "predicted_min_p50": 90,
        "predicted_min_p90": 110, "final_price": 55.0, "tip": 10.0,
        "note": "fifth visit in 0×shaved → n=5 exactly MIN_N",
    },
    {
        "key": "V6", "dog_key": "fluff", "visit_date": date(2026, 3, 5),
        "status": "completed", "condition_score": 5, "shaved_down": False,
        "pivoted": False, "actual_minutes": 45, "predicted_min_p50": 50,
        "predicted_min_p90": 70, "final_price": 50.0, "tip": 10.0,
        "note": "maintained coat; under-run",
    },
    # Fri 06 — null price, no prediction, cancelled
    {
        "key": "V7", "dog_key": "fluff", "visit_date": date(2026, 3, 6),
        "status": "completed", "condition_score": 5, "shaved_down": False,
        "pivoted": False, "actual_minutes": 40, "predicted_min_p50": 50,
        "predicted_min_p90": 70, "final_price": None, "tip": 0.0,
        "note": "NULL price → excluded from €/hour only",
    },
    {
        "key": "V8", "dog_key": "mix", "visit_date": date(2026, 3, 6),
        "status": "completed", "condition_score": 3, "shaved_down": False,
        "pivoted": False, "actual_minutes": 60, "predicted_min_p50": None,
        "predicted_min_p90": None, "final_price": 55.0, "tip": 0.0,
        "note": "no stored prediction → pivot yes, overrun/P90 no",
    },
    {
        "key": "V9", "dog_key": "mix", "visit_date": date(2026, 3, 6),
        "status": "cancelled", "condition_score": 2, "shaved_down": False,
        "pivoted": False, "actual_minutes": 30, "predicted_min_p50": 60,
        "predicted_min_p90": 80, "final_price": 40.0, "tip": 0.0,
        "note": "cancelled → excluded from every metric",
    },
    # Sat 07
    {
        "key": "V10", "dog_key": "mix", "visit_date": date(2026, 3, 7),
        "status": "no_show", "condition_score": 2, "shaved_down": False,
        "pivoted": False, "actual_minutes": 30, "predicted_min_p50": 60,
        "predicted_min_p90": 80, "final_price": 40.0, "tip": 0.0,
        "note": "no_show → excluded from every metric",
    },
]
# fmt: on


# ---------------------------------------------------------------------------
# EXPECTED — hand-computed from VISITS above. Arithmetic in comments.
# Metric SQL (#27–#29) must match these; do not regenerate from views.
# ---------------------------------------------------------------------------

# €/hour cell condition=0 × shaved=True: V1–V5
#   minutes = 120+100+95+90+85 = 490 → hours = 490/60
#   rev ex  = 70+65+60+60+55 = 310 → 310 / (490/60) = 18600/490 = 1860/49
#   tips    = 15+0+10+0+10 = 35 → rev inc = 345 → 20700/490 = 2070/49
_EUR_0_SHAVED_HOURS = 490 / 60
_EUR_0_SHAVED_EX = 310 / _EUR_0_SHAVED_HOURS
_EUR_0_SHAVED_INC = 345 / _EUR_0_SHAVED_HOURS

# Overrun (eligible + P50 present): V1–V7, V11, V12, V15 (n=10)
#   (30+10+5+0-5-5-10+5+10-20) / 10 = 20/10 = 2.0
_OVERRUN_AVG = 2.0

# P90 miss (same n=10): only V1 (120 > 110) → 1/10
_P90_MISS_RATE = 1 / 10

# Pivot: eligible V1–V8, V11, V12, V15 (n=11); pivoted true = V3 only → 1/11
_PIVOT_RATE = 1 / 11

# Utilization Tue 2026-03-03: V1, V2, V15
#   planned P50 = 90+90+100 = 280
#   planned P90 = 110+110+130 = 350 > BUFFER 240 → over_buffer
#   actual      = 120+100+80 = 300
#   missing_pred count = 0

EXPECTED: dict[str, Any] = {
    "min_n": MIN_N,
    "buffer_minutes": BUFFER_MINUTES,
    "week": {"start": WEEK_START, "end": WEEK_END},
    "empty_week": {"start": EMPTY_WEEK_START, "end": EMPTY_WEEK_END},
    # --- €/hour (week × condition × shaved); show_rate iff n >= MIN_N ---
    "eur_per_hour": {
        # n=5 → show
        (0, True): {
            "n": 5,
            "show_rate": True,
            "eur_per_hour_ex_tip": _EUR_0_SHAVED_EX,
            "eur_per_hour_inc_tip": _EUR_0_SHAVED_INC,
            "revenue_ex_tip": 310.0,
            "revenue_inc_tip": 345.0,
            "hours": _EUR_0_SHAVED_HOURS,
        },
        # V6 only (V7 excluded: NULL price); n=1 → hide rates
        (5, False): {
            "n": 1,
            "show_rate": False,
            "eur_per_hour_ex_tip": None,
            "eur_per_hour_inc_tip": None,
        },
        # V11 alone
        (4, False): {
            "n": 1,
            "show_rate": False,
            "eur_per_hour_ex_tip": None,
            "eur_per_hour_inc_tip": None,
        },
        # V12 alone — below MIN_N cell called out in the issue
        (4, True): {
            "n": 1,
            "show_rate": False,
            "eur_per_hour_ex_tip": None,
            "eur_per_hour_inc_tip": None,
        },
        # V15 alone
        (2, False): {
            "n": 1,
            "show_rate": False,
            "eur_per_hour_ex_tip": None,
            "eur_per_hour_inc_tip": None,
        },
        # V8 alone
        (3, False): {
            "n": 1,
            "show_rate": False,
            "eur_per_hour_ex_tip": None,
            "eur_per_hour_inc_tip": None,
        },
    },
    # --- week-level rates ---
    "pivot": {
        "n": 11,
        "pivoted_count": 1,
        "rate": _PIVOT_RATE,
        "show_rate": True,  # 11 >= MIN_N
    },
    # --- week summary (#155): totals, always shown (no MIN_N) ---
    # Eligible: V11,V12,V1,V2,V15,V3,V4,V5,V6,V7,V8 (exclude V9,V10)
    # minutes = 840
    # revenue ex  = 48+52+70+65+58+60+60+55+50+55 = 573  (V7 NULL price skipped)
    # tips on priced = 5+0+15+0+10+10+0+10+10+0 = 60 → inc = 633
    "week_summary": {
        date(2026, 3, 2): {  # ISO week start (Monday)
            "visit_count": 11,
            "groomed_minutes": 840,
            "revenue_ex_tip": 573.0,
            "revenue_inc_tip": 633.0,
        },
        # empty week 2026-03-09: no row expected
    },
    "overrun": {
        "n": 10,
        "avg_minutes": _OVERRUN_AVG,
        "show_rate": True,
    },
    "p90_miss": {
        "n": 10,
        "miss_count": 1,
        "rate": _P90_MISS_RATE,
        "show_rate": True,
    },
    # --- utilization by visit_date (eligible only) ---
    "utilization": {
        date(2026, 3, 2): {
            "n": 2,
            "planned_p50": 110,  # 50+60
            "planned_p90": 150,  # 70+80
            "actual_minutes": 125,  # 55+70
            "missing_prediction": 0,
            "over_buffer": False,  # 150 <= 240
        },
        date(2026, 3, 3): {
            "n": 3,
            "planned_p50": 280,
            "planned_p90": 350,
            "actual_minutes": 300,
            "missing_prediction": 0,
            "over_buffer": True,  # 350 > 240
        },
        date(2026, 3, 4): {
            "n": 2,
            "planned_p50": 180,
            "planned_p90": 220,
            "actual_minutes": 185,
            "missing_prediction": 0,
            "over_buffer": False,
        },
        date(2026, 3, 5): {
            "n": 2,
            "planned_p50": 140,  # 90+50
            "planned_p90": 180,  # 110+70
            "actual_minutes": 130,  # 85+45
            "missing_prediction": 0,
            "over_buffer": False,
        },
        date(2026, 3, 6): {
            "n": 2,  # V7, V8 (V9 cancelled)
            "planned_p50": 50,  # V7 only; V8 has no P50 — not treated as 0
            "planned_p90": 70,
            "actual_minutes": 100,  # 40+60
            "missing_prediction": 1,  # V8
            "over_buffer": False,
        },
        # Sat 03-07: only no_show → no utilization row
    },
}
