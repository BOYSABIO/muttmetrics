"""Breed catalog — list for Directory SPA pickers."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from muttmetrics.api.deps import get_db, require_api_key
from muttmetrics.api.schemas.breeds import BreedListItem
from muttmetrics.models.breed import Breed

router = APIRouter(tags=["breeds"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/breeds", dependencies=[Depends(require_api_key)])
def list_breeds(session: DbSession) -> list[BreedListItem]:
    """Return the seeded breed catalog for Directory selects."""
    rows = session.scalars(
        select(Breed).order_by(Breed.name_de.nulls_last(), Breed.name_en.nulls_last())
    ).all()
    return [BreedListItem.model_validate(row) for row in rows]
