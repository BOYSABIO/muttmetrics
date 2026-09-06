"""Protected ping — auth via require_api_key dependency."""

from fastapi import APIRouter, Depends

from muttmetrics.api.deps import require_api_key

router = APIRouter(tags=["auth"])


@router.get("/ping", dependencies=[Depends(require_api_key)])
def ping() -> dict[str, bool]:
    """Return ok only if X-API-Key matches settings.api_key."""
    return {"ok": True}
