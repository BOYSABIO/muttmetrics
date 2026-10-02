"""Shared pytest fixtures for the API test suite.

Local runs hit the same Docker Compose Postgres as day-to-day dev
(see docs/runbooks/db-peek.md). Prefer 127.0.0.1 over localhost on windows.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from muttmetrics.api.app import create_app

# Default matches .env.example / compose. CI can override via env.
_DEFAULT_DATABASE_URL = "postgresql+psycopg://muttmetrics:muttmetrics@127.0.0.1:5432/muttmetrics"
_DEFAULT_API_KEY = "test-api-key"


@pytest.fixture
def api_key() -> str:
    return os.environ.get("API_KEY", _DEFAULT_API_KEY)


@pytest.fixture
def auth_headers(api_key: str) -> dict[str, str]:
    return {"X-API-Key": api_key}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, api_key: str) -> TestClient:
    """App client with DATABASE_URL + API_KEY set for Settings."""
    monkeypatch.setenv(
        "DATABASE_URL",
        os.environ.get("DATABASE_URL", _DEFAULT_DATABASE_URL),
    )
    monkeypatch.setenv("API_KEY", api_key)
    return TestClient(create_app())
