"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# #187 — refuse the committed example and short keys so a copied .env
# cannot "work" with a published secret.
MIN_API_KEY_LENGTH = 24
INSECURE_API_KEYS = frozenset({"dev-change-me"})
_API_KEY_GENERATE_HINT = 'python -c "import secrets; print(secrets.token_urlsafe(32))"'


class Settings(BaseSettings):
    """
    Runtime configuration for MuttMetrics.

    Values come from environment variables (and optionally a local .env)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        ...,
        description="SQLAlchemy database URL",
    )

    api_key: str = Field(
        ...,
        description="Shared secret for X-API-Key header auth",
    )

    photo_root: Path = Field(
        default=Path.home() / "muttmetrics-data" / "photos",
        description="Directory where capture photos are stored (outside the repo)",
    )

    backup_root: Path = Field(
        default=Path.home() / "muttmetrics-data" / "backups",
        description="Directory for database dumps and the photo backup copy",
    )

    @field_validator("api_key")
    @classmethod
    def reject_insecure_api_key(cls, value: str) -> str:
        """Block the .env.example placeholder and short keys (#187)."""
        if value in INSECURE_API_KEYS or len(value) < MIN_API_KEY_LENGTH:
            raise ValueError(
                "API_KEY is insecure: it is the .env.example placeholder "
                f"(`dev-change-me`) or shorter than {MIN_API_KEY_LENGTH} characters. "
                "Generate a key with:\n"
                f"  {_API_KEY_GENERATE_HINT}\n"
                "Put the same value in `.env` (API_KEY) and "
                "`frontend/.env` (VITE_API_KEY), then restart the API."
            )
        return value


@lru_cache
def get_settings() -> Settings:
    """
    Load settings from the environment (API key, Postgres, paths), once.

    Cached: every request calls this (require_api_key), and re-reading `.env`
    each time was wasted work. A changed `.env` therefore needs a restart, the
    same as the database engine already did. Tests that change env vars call
    ``get_settings.cache_clear()`` (an autouse fixture in tests/conftest.py).

    Raises:
        ValidationError: if required settings such as DATABASE_URL are missing,
            or API_KEY is the insecure example / too short (#187).
    """
    return Settings()


__all__ = [
    "INSECURE_API_KEYS",
    "MIN_API_KEY_LENGTH",
    "Settings",
    "get_settings",
    "ValidationError",
]
