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
    condition_score: int
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
    utilization: list[UtilizationDayOut]
    utilization_weeks: list[UtilizationWeekOut]


class MetricsWeekOut(MetricsPeriodBlock):
    """Current week plus the prior Monday–Sunday block for vs-last-week curls."""

    previous_week: MetricsPeriodBlock | None = None


class MetricsPeriodOut(MetricsPeriodBlock):
    """Arbitrary range plus the immediately preceding equal-length range."""

    previous_period: MetricsPeriodBlock | None = None
