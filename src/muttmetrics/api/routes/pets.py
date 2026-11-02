"""Pet onboarding (create-or-get), directory search/profile, duration-range."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from muttmetrics.api.deps import get_db, require_api_key
from muttmetrics.api.schemas.duration_range import DurationRangeResponse
from muttmetrics.api.schemas.pets import (
    PatchPetRequest,
    PetProfile,
    PetResponse,
    PetSearchItem,
    UpsertPetRequest,
)
from muttmetrics.api.services.pets import (
    create_or_get_pet,
    get_pet_profile,
    patch_pet,
    search_pets,
)
from muttmetrics.services.visit_predictions import score_pet_duration_range

router = APIRouter(tags=["pets"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/pets", dependencies=[Depends(require_api_key)])
def upsert_pet(
    body: UpsertPetRequest,
    session: DbSession,
    response: Response,
) -> PetResponse:
    """Create a pet or return the existing one for this owner + name + species."""
    try:
        pet, created = create_or_get_pet(
            session,
            owner_id=body.owner_id,
            name=body.name,
            species=body.species,
            breed_id=body.breed_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    response.status_code = 201 if created else 200
    return PetResponse.model_validate(pet)


@router.get("/pets", dependencies=[Depends(require_api_key)])
def list_pets(
    session: DbSession,
    q: str | None = Query(default=None, description="Substring match on pet name"),
) -> list[PetSearchItem]:
    """Directory search / browse - pet rows with owner_name for the UI."""
    return search_pets(session, q=q)


@router.get(
    "/pets/{pet_id}/duration-range",
    dependencies=[Depends(require_api_key)],
)
def get_duration_range(
    pet_id: int,
    session: DbSession,
    as_of: Annotated[
        date | None,
        Query(description="Date for days_since_last (default: today)"),
    ] = None,
    service_id: Annotated[
        int | None,
        Query(description="Booked service id (validated; not in formula v0)"),
    ] = None,
) -> DurationRangeResponse:
    """Preview P50/P90 for a pet without creating a visit (#26)."""
    try:
        result = score_pet_duration_range(
            session,
            pet_id=pet_id,
            as_of=as_of or date.today(),
            service_id=service_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return DurationRangeResponse(
        pet_id=result.pet_id,
        service_id=result.service_id,
        as_of=result.as_of,
        days_since_last=result.days_since_last,
        predicted_min_p50=result.predicted_min_p50,
        predicted_min_p90=result.predicted_min_p90,
        skipped_reason=result.skipped_reason,
    )


@router.get("/pets/{pet_id}", dependencies=[Depends(require_api_key)])
def read_pet(
    pet_id: int,
    session: DbSession,
    recent_limit: Annotated[
        int,
        Query(ge=0, le=50, description="Max recent visits to include"),
    ] = 10,
) -> PetProfile:
    """Directory profile: pet fields, owner summary, recent visits (#131)."""
    try:
        return get_pet_profile(session, pet_id=pet_id, recent_limit=recent_limit)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/pets/{pet_id}", dependencies=[Depends(require_api_key)])
def update_pet(
    pet_id: int,
    body: PatchPetRequest,
    session: DbSession,
) -> PetProfile:
    """Directory: partial update of hand-entered pet fields."""
    try:
        return patch_pet(session, pet_id=pet_id, body=body)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
