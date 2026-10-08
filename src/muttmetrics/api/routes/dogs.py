"""Dog onboarding (create-or-get), directory search/profile, duration-range."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from muttmetrics.api.deps import get_db, require_api_key
from muttmetrics.api.schemas.dogs import (
    DogProfile,
    DogResponse,
    DogSearchItem,
    UpsertDogRequest,
)
from muttmetrics.api.schemas.duration_range import DurationRangeResponse
from muttmetrics.api.services.dogs import create_or_get_dog, get_dog_profile, search_dogs
from muttmetrics.api.services.visit_predictions import score_dog_duration_range

router = APIRouter(tags=["dogs"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/dogs", dependencies=[Depends(require_api_key)])
def upsert_dog(
    body: UpsertDogRequest,
    session: DbSession,
    response: Response,
) -> DogResponse:
    """Create a dog or return the existing one for this owner + name."""
    try:
        dog, created = create_or_get_dog(
            session,
            owner_id=body.owner_id,
            name=body.name,
            breed_id=body.breed_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    response.status_code = 201 if created else 200
    return DogResponse.model_validate(dog)


@router.get("/dogs", dependencies=[Depends(require_api_key)])
def list_dogs(
    session: DbSession,
    q: str | None = Query(default=None, description="Substring match on dog name"),
) -> list[DogSearchItem]:
    """Directory search / browse - dog rows with owner_name for the UI."""
    return search_dogs(session, q=q)


@router.get(
    "/dogs/{dog_id}/duration-range",
    dependencies=[Depends(require_api_key)],
)
def get_duration_range(
    dog_id: int,
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
    """Preview P50/P90 for a dog without creating a visit (#26)."""
    try:
        result = score_dog_duration_range(
            session,
            dog_id=dog_id,
            as_of=as_of or date.today(),
            service_id=service_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return DurationRangeResponse(
        dog_id=result.dog_id,
        service_id=result.service_id,
        as_of=result.as_of,
        days_since_last=result.days_since_last,
        predicted_min_p50=result.predicted_min_p50,
        predicted_min_p90=result.predicted_min_p90,
        skipped_reason=result.skipped_reason,
    )


@router.get("/dogs/{dog_id}", dependencies=[Depends(require_api_key)])
def read_dog(
    dog_id: int,
    session: DbSession,
    recent_limit: Annotated[
        int,
        Query(ge=0, le=50, description="Max recent visits to include"),
    ] = 10,
) -> DogProfile:
    """Directory profile: dog fields, owner summary, recent visits (#131)."""
    try:
        return get_dog_profile(session, dog_id=dog_id, recent_limit=recent_limit)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
