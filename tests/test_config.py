"""Tests for environment-backed settings."""

import pytest
from pydantic import ValidationError

from muttmetrics.config import Settings, get_settings


def test_settings_loads_database_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the database URL is loaded from the environment."""

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://muttmetrics:muttmetrics@localhost:5432/muttmetrics",
    )
    settings = Settings(_env_file=None)
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_get_settings_returns_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify get_settings returns a Settings instance."""

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://muttmetrics:muttmetrics@localhost:5432/muttmetrics",
    )
    settings = get_settings()
    assert "postgresql" in settings.database_url


def test_missing_database_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify missing DATABASE_URL raises a ValidationError."""

    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
