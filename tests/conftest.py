"""Shared pytest fixtures for the API test suite.

Local runs hit the same Docker Compose Postgres as day-to-day dev
(see docs/runbooks/db-peek.md). Prefer 127.0.0.1 over localhost on windows.
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
from muttmetrics.db.session import get_engine
from tests.fixtures.load_metric_month import load_metric_month
from tests.fixtures.load_metric_week import load_metric_week

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
def db_connection(monkeypatch: pytest.MonkeyPatch) -> Generator:
    """One DB connection wrapped in a transaction that always rolls back."""
    monkeypatch.setenv(
        "DATABASE_URL",
        os.environ.get("DATABASE_URL", _DEFAULT_DATABASE_URL),
    )
    # Settings may already be cached from an earlier import - clear if your
    # project caches them. For now we only set the env before get_engine()

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
    monkeypatch.setenv(
        "DATABASE_URL",
        os.environ.get("DATABASE_URL", _DEFAULT_DATABASE_URL),
    )
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
