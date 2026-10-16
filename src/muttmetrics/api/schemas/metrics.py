"""Pydantic models for GET /metrics/week (#156 / #158)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class MetricValue(BaseModel):
    """A rate/average that may be hidden under MIN_N."""

    value: float | None
    reason: str | None = None  # e.g. "not_enough_data"


class WeekSummaryOut(BaseModel):
    visit_count: int
    groomed_minutes: int
    revenue_ex_tip: float
    revenue_inc_tip: float
    # Overall week €/hour (glossary eligibility; MIN_N in SQL)
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


class MetricsWeekBlock(BaseModel):
    """One week's packaged metrics (no nested previous)."""

    week_start: date
    week_end: date
    buffer_minutes: int
    min_n: int
    summary: WeekSummaryOut
    eur_per_hour: list[EurPerHourCellOut]
    pivot: PivotOut
    overrun: OverrunOut
    p90_miss: P90MissOut
    utilization: list[UtilizationDayOut]


class MetricsWeekOut(MetricsWeekBlock):
    """Current week plus the prior Monday–Sunday block for vs-last-week UI."""

    previous_week: MetricsWeekBlock | None = None
