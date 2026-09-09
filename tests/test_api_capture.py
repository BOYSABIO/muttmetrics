"""HTML capture form (issue #63)."""

import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient

from muttmetrics.api.app import create_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://muttmetrics:muttmetrics@localhost:5432/muttmetrics",
    )
    monkeypatch.setenv("API_KEY", "test-api-key")
    return TestClient(create_app())


def test_get_capture_returns_html_form(client: TestClient) -> None:
    response = client.get("/capture")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'name="owner_name"' in response.text
    assert 'name="actual_minutes"' in response.text


def test_post_capture_creates_visit(client: TestClient) -> None:
    suffix = str(uuid.uuid4().hex)[:8]
    response = client.post(
        "/capture",
        data={
            "owner_name": f"Capture Owner {suffix}",
            "dog_name": f"Capture Dog {suffix}",
            "visit_date": date.today().isoformat(),
            "actual_minutes": "90",
            "condition_score": "3",
            "what_surprised_me": "calm today",
        },
    )
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Saved" in response.text
    assert "Visit #" in response.text
