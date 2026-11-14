"""Breed catalog: list for pickers, and add a breed in the salon."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from muttmetrics.api.deps import get_db, require_api_key
from muttmetrics.api.schemas.breeds import BreedListItem, CreateBreedRequest
from muttmetrics.models.breed import Breed

router = APIRouter(tags=["breeds"])

DbSession = Annotated[Session, Depends(get_db)]


def normalize_breed_name(raw: str) -> str:
    """Collapse spaces; capitalise words only if everything was typed lower-case
    ("golden retriever" -> "Golden Retriever", "Coton de Tuléar" kept)."""
    cleaned = " ".join(raw.split())
    return cleaned.title() if cleaned == cleaned.lower() else cleaned


@router.get("/breeds", dependencies=[Depends(require_api_key)])
def list_breeds(
    session: DbSession,
    species: Annotated[
        Literal["dog", "cat"] | None,
        Query(description="Filter by species; omit for the full catalog"),
    ] = None,
) -> list[BreedListItem]:
    """Return the breed catalog for pickers, by English name."""
    stmt = select(Breed).order_by(Breed.name_en.nulls_last(), Breed.name_de.nulls_last())
    if species is not None:
        stmt = stmt.where(Breed.species == species)
    rows = session.scalars(stmt).all()
    return [BreedListItem.model_validate(row) for row in rows]


@router.post(
    "/breeds",
    dependencies=[Depends(require_api_key)],
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "A breed with this name exists; detail.breed is it"}},
)
def create_breed(session: DbSession, body: CreateBreedRequest) -> BreedListItem:
    """Add a breed the catalog doesn't have. It has no typical minutes, so the
    rules estimate stays empty for its dogs until someone sets them.

    One breed per name per species, any capitalisation, also matching the
    German name: the existing breed comes back with 409 instead of a twin.
    """
    name = normalize_breed_name(body.name_en)
    if len(name) < 2:
        raise HTTPException(status_code=422, detail="Breed name is too short")
    lowered = name.lower()
    existing = session.scalar(
        select(Breed).where(
            Breed.species == body.species,
            or_(func.lower(Breed.name_en) == lowered, func.lower(Breed.name_de) == lowered),
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"{existing.name_en or existing.name_de} is already a breed",
                "breed": BreedListItem.model_validate(existing).model_dump(),
            },
        )
    breed = Breed(species=body.species, name_en=name, source="salon")
    session.add(breed)
    session.flush()
    return BreedListItem.model_validate(breed)
