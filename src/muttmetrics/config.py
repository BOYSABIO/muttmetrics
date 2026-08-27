"""Application settings loaded from environment variables."""

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


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


def get_settings() -> Settings:
    """
    Load settings from the environment.

    Raises:
        ValidationError: if required settings such as DATABASE_URL are missing.
    """
    return Settings()


__all__ = [
    "Settings",
    "get_settings",
    "ValidationError",
]
