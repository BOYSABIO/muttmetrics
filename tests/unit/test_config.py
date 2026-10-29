"""Tests for environment-backed settings."""

import pytest
from pydantic import ValidationError

from muttmetrics.config import (
    INSECURE_API_KEYS,
    MIN_API_KEY_LENGTH,
    Settings,
    get_settings,
)

_TEST_API_KEY = "test-api-key-not-for-production"


def _set_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Minimal env so Settings can construct in tests."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://muttmetrics:muttmetrics@127.0.0.1:5432/muttmetrics",
    )
    monkeypatch.setenv("API_KEY", _TEST_API_KEY)


def test_settings_loads_database_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the database URL is loaded from the environment."""

    _set_required_env(monkeypatch)
    settings = Settings(_env_file=None)
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_settings_loads_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the API key is loaded from the environment."""

    _set_required_env(monkeypatch)
    settings = Settings(_env_file=None)
    assert settings.api_key == _TEST_API_KEY


def test_get_settings_returns_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify get_settings returns a Settings instance."""

    _set_required_env(monkeypatch)
    settings = get_settings()
    assert "postgresql" in settings.database_url
    assert settings.api_key == _TEST_API_KEY


def test_missing_database_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify missing DATABASE_URL raises a ValidationError."""

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("API_KEY", _TEST_API_KEY)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify missing API_KEY raises a ValidationError."""

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://muttmetrics:muttmetrics@127.0.0.1:5432/muttmetrics",
    )
    monkeypatch.delenv("API_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize("bad_key", sorted(INSECURE_API_KEYS) + ["short-key"])
def test_insecure_api_key_raises(monkeypatch: pytest.MonkeyPatch, bad_key: str) -> None:
    """Example placeholder and short keys must not start the API (#187)."""
    assert bad_key in INSECURE_API_KEYS or len(bad_key) < MIN_API_KEY_LENGTH
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://muttmetrics:muttmetrics@127.0.0.1:5432/muttmetrics",
    )
    monkeypatch.setenv("API_KEY", bad_key)
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    msg = str(exc_info.value)
    assert "insecure" in msg.lower()
    assert "secrets.token_urlsafe" in msg
