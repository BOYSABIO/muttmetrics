"""Shared pytest fixtures for the API test suite.

Tests run against a separate database, ``muttmetrics_test`` by default, never
the one the salon uses (#177). Override with TEST_DATABASE_URL. Prefer
127.0.0.1 over localhost on Windows.
"""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from muttmetrics.api.app import create_app
from muttmetrics.api.deps import get_db
from muttmetrics.config import get_settings
from muttmetrics.db.session import get_engine
from tests.db_guard import DEFAULT_TEST_DATABASE_URL, require_test_database
from tests.fixtures.load_metric_month import load_metric_month
from tests.fixtures.load_metric_week import load_metric_week

# Long enough for #187 (MIN_API_KEY_LENGTH); not the .env.example placeholder.
_DEFAULT_API_KEY = "test-api-key-not-for-production"


def pytest_configure(config: pytest.Config) -> None:
    """Point the whole run at the test database, or stop before any test runs.

    Runs once, before collection and before anything calls get_engine(), so
    every engine the app creates during the run uses this URL.
    """
    url = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
    try:
        os.environ["DATABASE_URL"] = require_test_database(url)
    except ValueError as exc:
        raise pytest.UsageError(str(exc)) from exc
    # Health/error tests call create_app() without the client fixture; give
    # them a key that passes the #187 length / placeholder checks.
    os.environ.setdefault("API_KEY", _DEFAULT_API_KEY)


@pytest.fixture(autouse=True)
def _fresh_settings() -> Generator[None]:
    """get_settings() is cached (#180). Tests that monkeypatch env vars
    (API_KEY, PHOTO_ROOT, ...) need it re-read, so clear before and after each test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def api_key() -> str:
    return os.environ.get("API_KEY", _DEFAULT_API_KEY)


@pytest.fixture
def auth_headers(api_key: str) -> dict[str, str]:
    return {"X-API-Key": api_key}


@pytest.fixture
def db_connection() -> Generator:
    """One DB connection wrapped in a transaction that always rolls back."""
    engine: Engine = get_engine()
    connection = engine.connect()
    transaction = connection.begin()  # open scratch pad
    try:
        yield connection
    finally:
        transaction.rollback()  # erase everything done on this connection
        connection.close()


@pytest.fixture
def db_session(db_connection) -> Generator[Session]:
    """ORM session that writes into the rollback scratchpad."""
    session = Session(
        bind=db_connection,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
    api_key: str,
    db_session: Session,
) -> Generator[TestClient]:
    """App client whose DB writes share the rollback scratchpad."""
    monkeypatch.setenv("API_KEY", api_key)

    app = create_app()

    def _override_get_db() -> Generator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def metric_week(db_session: Session) -> dict[str, dict[str, int]]:
    """Synthetic metric week loaded onto the rollback pad."""
    return load_metric_week(db_session)


@pytest.fixture
def metric_month(db_session: Session) -> dict[str, dict[str, int]]:
    """Synthetic metric month (weeks thin, month unlocks) for #170."""
    return load_metric_month(db_session)
