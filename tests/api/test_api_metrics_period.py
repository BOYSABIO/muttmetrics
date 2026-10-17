"""GET /metrics/period — range packaging + previous_period (#170)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from tests.fixtures.metric_month import EXPECTED, MONTH_END, MONTH_START
from tests.fixtures.metric_week import BUFFER_MINUTES, WEEK_END, WEEK_START
from tests.fixtures.metric_week import EXPECTED as WEEK_EXPECTED


def test_period_requires_auth(client: TestClient) -> None:
    assert (
        client.get(
            "/metrics/period",
            params={"start": str(MONTH_START), "end": str(MONTH_END)},
        ).status_code
        == 401
    )


def test_period_rejects_inverted_and_absurd_range(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    bad = client.get(
        "/metrics/period",
        headers=auth_headers,
        params={"start": str(MONTH_END), "end": str(MONTH_START)},
    )
    assert bad.status_code == 422

    huge_end = MONTH_START + timedelta(days=400)
    huge = client.get(
        "/metrics/period",
        headers=auth_headers,
        params={"start": str(MONTH_START), "end": str(huge_end)},
    )
    assert huge.status_code == 422


def test_period_month_matches_fixture(
    client: TestClient, auth_headers: dict[str, str], metric_month: dict
) -> None:
    res = client.get(
        "/metrics/period",
        headers=auth_headers,
        params={
            "start": str(MONTH_START),
            "end": str(MONTH_END),
            "buffer_minutes": BUFFER_MINUTES,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["period"] == "month"
    assert data["week_start"] == str(MONTH_START)
    assert data["week_end"] == str(MONTH_END)

    exp = EXPECTED["summary"]
    assert data["summary"]["visit_count"] == exp["visit_count"]
    assert data["summary"]["eur_per_hour_n"] == exp["eur_per_hour_n"]
    assert data["summary"]["eur_per_hour_inc_tip"]["value"] == pytest.approx(
        exp["eur_per_hour_inc_tip"]
    )
    assert data["summary"]["eur_per_hour_inc_tip"]["reason"] is None

    prev = data["previous_period"]
    assert prev is not None
    assert prev["period"] == "month"
    assert prev["week_start"] == "2026-03-01"
    assert prev["week_end"] == "2026-03-31"
    assert date.fromisoformat(prev["week_end"]) == MONTH_START - timedelta(days=1)


def test_period_week_range_matches_week_fixture(
    client: TestClient, auth_headers: dict[str, str], metric_week: dict
) -> None:
    """Same numbers as /metrics/week when start/end are Mon–Sun."""
    res = client.get(
        "/metrics/period",
        headers=auth_headers,
        params={
            "start": str(WEEK_START),
            "end": str(WEEK_END),
            "buffer_minutes": BUFFER_MINUTES,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["period"] == "week"
    exp = WEEK_EXPECTED["week_summary"][WEEK_START]
    assert data["summary"]["visit_count"] == exp["visit_count"]
    assert data["summary"]["eur_per_hour_n"] == exp["eur_per_hour_n"]


def test_period_max_range_counts_days_inclusively(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """#177: 366 inclusive days is allowed; 367 is not."""
    start = date(2026, 1, 1)
    ok = client.get(
        "/metrics/period",
        headers=auth_headers,
        params={"start": str(start), "end": str(start + timedelta(days=365))},
    )
    assert ok.status_code == 200

    too_long = client.get(
        "/metrics/period",
        headers=auth_headers,
        params={"start": str(start), "end": str(start + timedelta(days=366))},
    )
    assert too_long.status_code == 422


def test_period_month_returns_weekly_rollup_from_sql(
    client: TestClient, auth_headers: dict[str, str], metric_month: dict
) -> None:
    """#178: month mode reads weeks from the API, edge weeks clipped to the month."""
    res = client.get(
        "/metrics/period",
        headers=auth_headers,
        params={
            "start": str(MONTH_START),
            "end": str(MONTH_END),
            "buffer_minutes": BUFFER_MINUTES,
        },
    )
    assert res.status_code == 200
    weeks = res.json()["utilization_weeks"]
    assert [w["week_start"] for w in weeks] == [str(d) for d in EXPECTED["utilization_weeks"]]
    first = weeks[0]
    assert first["range_start"] == str(MONTH_START)  # not Mar 30
    assert first["range_end"] == "2026-04-05"
    assert first["over_buffer_days"] == 0
    assert "over_buffer" not in first  # no weekly total vs daily cap
