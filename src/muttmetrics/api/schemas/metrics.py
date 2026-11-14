"""Pydantic models for GET /metrics/week and /metrics/period (#156 / #170 / #187)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

PeriodKind = Literal["week", "month", "custom"]


class MetricValue(BaseModel):
    """A rate/average that may be hidden under MIN_N."""

    value: float | None
    reason: str | None = None  # e.g. "not_enough_data"


class PeriodSummaryOut(BaseModel):
    """Headline totals for one inclusive range (week, month, or custom)."""

    visit_count: int
    groomed_minutes: int
    revenue_ex_tip: float
    revenue_inc_tip: float
    # Overall period €/hour (glossary eligibility; MIN_N in SQL)
    eur_per_hour_n: int
    eur_per_hour_ex_tip: MetricValue
    eur_per_hour_inc_tip: MetricValue


class EurPerHourCellOut(BaseModel):
    """One € / hour cell: a coat condition (unshaved visits), or every
    shave-down together (``shaved_down`` true, ``condition_score`` null)."""

    condition_score: int | None
    shaved_down: bool
    n: int
    groomed_minutes: int | None = None
    hours: float | None = None
    revenue_ex_tip: float | None = None
    revenue_inc_tip: float | None = None
    eur_per_hour_ex_tip: MetricValue
    eur_per_hour_inc_tip: MetricValue


class PivotOut(BaseModel):
    n: int
    pivoted_count: int
    rate: MetricValue


class OverrunOut(BaseModel):
    n: int
    avg_minutes: MetricValue


class P90MissOut(BaseModel):
    n: int
    miss_count: int
    rate: MetricValue


class EstimateBandsOut(BaseModel):
    """Where grooms with an estimate landed: within P50, within P90, past P90.

    Counts are facts; ``enough`` is n >= MIN_N (proportions are drawn only then).
    """

    n: int
    within_p50: int
    within_p90: int
    past_p90: int
    enough: bool


class UtilizationDayOut(BaseModel):
    visit_date: date
    n: int
    planned_p50: int
    planned_p90: int
    actual_minutes: int
    missing_prediction: int
    over_buffer: bool


class UtilizationWeekOut(BaseModel):
    """One ISO week of ``metric_utilization_weeks`` (#178).

    ``week_start`` here is the Monday of that utilization row (SQL grain), not
    the API period bounds. ``range_start`` / ``range_end`` are clipped to the
    requested period. There is deliberately no weekly ``over_buffer``: the cap
    is per day, so a week reports how many of its days went over.
    """

    week_start: date
    range_start: date
    range_end: date
    day_count: int
    n: int
    planned_p50: int
    planned_p90: int
    actual_minutes: int
    missing_prediction: int
    over_buffer_days: int


class MetricsPeriodBlock(BaseModel):
    """One inclusive date range of packaged metrics (no nested previous).

    ``start`` / ``end`` are the range bounds (#187). For a week they are
    Monday…Sunday; for a month the 1st…last day.
    """

    period: PeriodKind
    start: date
    end: date
    buffer_minutes: int
    min_n: int
    summary: PeriodSummaryOut
    eur_per_hour: list[EurPerHourCellOut]
    pivot: PivotOut
    overrun: OverrunOut
    p90_miss: P90MissOut
    estimate_bands: EstimateBandsOut
    utilization: list[UtilizationDayOut]
    utilization_weeks: list[UtilizationWeekOut]


class MetricsWeekOut(MetricsPeriodBlock):
    """Current week plus the prior Monday–Sunday block for vs-last-week curls."""

    previous_week: MetricsPeriodBlock | None = None


class AllTimeOut(BaseModel):
    """Totals from the first completed visit through ``through`` (today)."""

    first_visit_date: date
    through: date
    summary: PeriodSummaryOut


class MetricsPeriodOut(MetricsPeriodBlock):
    """Arbitrary range plus the preceding range, a recent window and all-time totals.

    ``previous_period`` is the immediately preceding range. While the requested
    range is still running (today inside it), it is clipped to the same number
    of elapsed days, so Tuesday isn't compared with a whole week
    (``previous_is_partial``).

    ``recent`` is the ``recent_days`` window ending at the range end (or today,
    whichever is earlier), for slow questions that a week can't answer:
    € / hour by coat, how good the time estimates are.
    """

    previous_period: MetricsPeriodBlock | None = None
    previous_is_partial: bool = False
    recent_days: int | None = None
    recent: MetricsPeriodBlock | None = None
    all_time: AllTimeOut | None = None
