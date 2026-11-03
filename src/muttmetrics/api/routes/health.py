"""Liveness endpoint - process is up (#197 also reports version)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from muttmetrics import __version__

router = APIRouter(tags=["health"])


def _alembic_head() -> str | None:
    """Current DB revision, or None if Postgres is unreachable.

    Health stays 200 even when the DB is down — version is still useful for
    "which build is answering?" Alembic head is best-effort.
    """
    try:
        from muttmetrics.db.session import get_engine

        with get_engine().connect() as conn:
            row = conn.execute(text("SELECT version_num FROM alembic_version")).first()
            return str(row[0]) if row else None
    except Exception:
        return None


@router.get("/health")
def health() -> dict[str, Any]:
    """Return 200 when the API process can answer HTTP."""
    return {
        "status": "ok",
        "version": __version__,
        "alembic_head": _alembic_head(),
    }
