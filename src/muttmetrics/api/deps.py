"""Shared FastAPI dependencies (auth, later DB session, etc.)."""

import secrets
from collections.abc import Generator

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from muttmetrics.config import get_settings
from muttmetrics.db.session import get_session_factory

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(x_api_key: str | None = Depends(api_key_header)) -> None:
    """Reject the request unless X-API-Key matches settings.api_key."""
    expected = get_settings().api_key
    if x_api_key is None or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )


def get_db() -> Generator[Session]:
    """Yield a DB session; commit on success, rollback on error."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
