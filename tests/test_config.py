"""Tests for environment-backed settings."""

import pytest
from pydantic import ValidationError

from muttmetrics.config import Settings, get_settings


def _set_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Minimal env so Settings can construct in tests."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://muttmetrics:muttmetrics@localhost:5432/muttmetrics",
    )
    monkeypatch.setenv("API_KEY", "test-api-key")


def test_settings_loads_database_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the database URL is loaded from the environment."""

    _set_required_env(monkeypatch)
    settings = Settings(_env_file=None)
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_settings_loads_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the API key is loaded from the environment."""

    _set_required_env(monkeypatch)
    settings = Settings(_env_file=None)
    assert settings.api_key == "test-api-key"


def test_get_settings_returns_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify get_settings returns a Settings instance."""

    _set_required_env(monkeypatch)
    settings = get_settings()
    assert "postgresql" in settings.database_url
    assert settings.api_key == "test-api-key"


def test_missing_database_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify missing DATABASE_URL raises a ValidationError."""

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("API_KEY", "test-api-key")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify missing API_KEY raises a ValidationError."""

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://muttmetrics:muttmetrics@localhost:5432/muttmetrics",
    )
    monkeypatch.delenv("API_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
