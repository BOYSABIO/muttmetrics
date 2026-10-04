"""Rules-based duration period (P50/P90). Pure functions, no DB, no I/O.

See docs/prior.md and issue #23."""

from __future__ import annotations

from typing import Literal

SizeBand = Literal["s", "m", "l", "xl"]

_SIZE_MULT: dict[str, float] = {
    "s": 0.85,
    "m": 1.0,
    "l": 1.15,
    "xl": 1.30,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def rules_prior(
    *,
    base_groom_minutes: int,
    matting_risk: int = 1,
    size_band: SizeBand | str | None = None,
    days_since_last: int | None = None,
    recommended_interval_days: int | None = None,
    handling_score: int | None = None,
) -> tuple[int, int]:
    """Return (p50, p90) minutes from hand-encoded rules.

    P90 is always >= P50. Same inputs always return the same pair.
    """
    if base_groom_minutes <= 0:
        raise ValueError("base_groom_minutes must be positive")
    if not 1 <= matting_risk <= 5:
        raise ValueError("matting_risk must be between 1 and 5")
    if handling_score is not None and not 1 <= handling_score <= 5:
        raise ValueError("handling_score must be between 1 and 5")

    size_mult = _SIZE_MULT.get(size_band or "", 1.0)
    matting_mult = 1.0 + 0.10 * (matting_risk - 1)

    overdue: float | None = None
    if (
        days_since_last is not None
        and recommended_interval_days is not None
        and recommended_interval_days > 0
    ):
        overdue = days_since_last / recommended_interval_days
        interval_mult = _clamp(0.9 + 0.20 * overdue, 0.90, 1.50)
    else:
        interval_mult = 1.0

    if handling_score is None:
        handling_mult = 1.0
    else:
        handling_mult = _clamp(1.0 + 0.05 * (handling_score - 3), 0.90, 1.20)

    p50 = round(base_groom_minutes * size_mult * matting_mult * interval_mult * handling_mult)

    spread_frac = 0.20 + 0.05 * (matting_risk - 1)
    if overdue is not None and overdue > 1:
        spread_frac += 0.10 * min(overdue - 1, 1.0)

    p90 = max(p50, round(p50 * (1 + spread_frac)))
    return p50, p90
