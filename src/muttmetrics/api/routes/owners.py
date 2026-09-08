"""Owner onboarding - create-or-get by name."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from muttmetrics.api.deps import get_db, require_api_key
from muttmetrics.api.schemas.owners import OwnerResponse, UpsertOwnerRequest
from muttmetrics.api.services.owners import create_or_get_owner

router = APIRouter(tags=["owners"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/owners", dependencies=[Depends(require_api_key)])
def upsert_owner(
    body: UpsertOwnerRequest,
    session: DbSession,
    response: Response,
) -> OwnerResponse:
    """Create an owner or return the existing one with the same name."""
    try:
        owner, created = create_or_get_owner(
            session,
            name=body.name,
            phone=body.phone,
            email=body.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    response.status_code = 201 if created else 200
    return OwnerResponse.model_validate(owner)
