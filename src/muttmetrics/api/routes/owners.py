"""Owner onboarding (create-or-get), search, and Directory profile reads."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from muttmetrics.api.deps import get_db, require_api_key
from muttmetrics.api.schemas.owners import (
    OwnerConflictCandidate,
    OwnerNameConflictDetail,
    OwnerProfile,
    OwnerResponse,
    OwnerSearchItem,
    PatchOwnerRequest,
    UpsertOwnerRequest,
)
from muttmetrics.api.services.owners import (
    OwnerNameConflict,
    create_or_get_owner,
    get_owner_profile,
    patch_owner,
    search_owners,
)

router = APIRouter(tags=["owners"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/owners", dependencies=[Depends(require_api_key)])
def list_owners(
    session: DbSession,
    q: str | None = Query(default=None, description="Substring match on owner name"),
) -> list[OwnerSearchItem]:
    """Browse/search owners for capture 'Already a client?' (#191)."""
    return search_owners(session, q=q)


@router.post("/owners", dependencies=[Depends(require_api_key)])
def upsert_owner(
    body: UpsertOwnerRequest,
    session: DbSession,
    response: Response,
) -> OwnerResponse:
    """
    Create an owner, or reuse when name+phone clearly match.

    Same name without a distinguishing phone → 409 with candidates (#187).
    """
    try:
        owner, created = create_or_get_owner(
            session,
            name=body.name,
            phone=body.phone,
            email=body.email,
        )
    except OwnerNameConflict as exc:
        detail = OwnerNameConflictDetail(
            message=(
                "An owner with this name already exists. "
                "Pick one from candidates, or send a phone to create another."
            ),
            candidates=[
                OwnerConflictCandidate(
                    owner_id=o.owner_id,
                    name=o.name,
                    phone=o.phone,
                )
                for o in exc.candidates
            ],
        )
        raise HTTPException(status_code=409, detail=detail.model_dump()) from exc
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
