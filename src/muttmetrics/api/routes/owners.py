"""Owner onboarding (create-or-get) and Directory profile reads."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from muttmetrics.api.deps import get_db, require_api_key
from muttmetrics.api.schemas.owners import (
    OwnerProfile,
    OwnerResponse,
    PatchOwnerRequest,
    UpsertOwnerRequest,
)
from muttmetrics.api.services.owners import (
    create_or_get_owner,
    get_owner_profile,
    patch_owner,
)

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


@router.get("/owners/{owner_id}", dependencies=[Depends(require_api_key)])
def read_owner(owner_id: int, session: DbSession) -> OwnerProfile:
    """Directory profile: owner contact fields + dog list (#131)."""
    try:
        return get_owner_profile(session, owner_id=owner_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/owners/{owner_id}", dependencies=[Depends(require_api_key)])
def update_owner(
    owner_id: int,
    body: PatchOwnerRequest,
    session: DbSession,
) -> OwnerProfile:
    """Directory: partial update of hand-entered owner fields."""
    try:
        return patch_owner(session, owner_id=owner_id, body=body)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
