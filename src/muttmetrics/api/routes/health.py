"""Liveness endpoint - process is up (does not check postgres)"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Return 200 when the API process can answer HTTP."""
    return {"status": "ok"}
