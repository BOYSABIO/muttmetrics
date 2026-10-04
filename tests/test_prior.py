"""Deterministic tests for the rules-based duration prior (#23)."""

import pytest

from muttmetrics.prior import rules_prior


def test_walkthrough_example() -> None:
    """Lesson walkthrough: large, high mat, overdue → (188, 263)."""
    p50, p90 = rules_prior(
        base_groom_minutes=100,
        matting_risk=4,
        size_band="l",
        days_since_last=90,
        recommended_interval_days=60,
        handling_score=4,
    )
    assert (p50, p90) == (188, 263)


def test_p90_always_ge_p50() -> None:
    p50, p90 = rules_prior(base_groom_minutes=40, matting_risk=1)
    assert p90 >= p50


def test_higher_matting_raises_or_widens() -> None:
    low = rules_prior(base_groom_minutes=80, matting_risk=1, size_band="m")
    high = rules_prior(base_groom_minutes=80, matting_risk=5, size_band="m")
    assert high[0] >= low[0]
    assert (high[1] - high[0]) >= (low[1] - low[0])


def test_overdue_raises_or_widens() -> None:
    on_time = rules_prior(
        base_groom_minutes=80,
        matting_risk=2,
        days_since_last=60,
        recommended_interval_days=60,
    )
    late = rules_prior(
        base_groom_minutes=80,
        matting_risk=2,
        days_since_last=120,
        recommended_interval_days=60,
    )
    assert late[0] >= on_time[0]
    assert (late[1] - late[0]) >= (on_time[1] - on_time[0])


def test_rejects_bad_base() -> None:
    with pytest.raises(ValueError):
        rules_prior(base_groom_minutes=0)
