"""Dog onboarding - create-or-get by owner + name."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from muttmetrics.api.deps import get_db, require_api_key
from muttmetrics.api.schemas.dogs import DogResponse, UpsertDogRequest
from muttmetrics.api.services.dogs import create_or_get_dog

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
