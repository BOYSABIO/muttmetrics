"""Service catalog - list packages for capture."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from muttmetrics.api.deps import get_db, require_api_key
from muttmetrics.api.schemas.services import ServiceListItem
from muttmetrics.models.service import Service

router = APIRouter(tags=["services"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/services", dependencies=[Depends(require_api_key)])
def list_services(
    session: DbSession,
    species: Annotated[
        Literal["dog", "cat"] | None,
        Query(description="Include this species plus untagged (NULL = all) services"),
    ] = None,
) -> list[ServiceListItem]:
    """Return the seeded service catalog for the SPA picker."""
    stmt = select(Service).order_by(Service.base_minutes.nulls_last(), Service.service_id)
    if species is not None:
        stmt = stmt.where(or_(Service.species == species, Service.species.is_(None)))
    rows = session.scalars(stmt).all()
    return [ServiceListItem.model_validate(row) for row in rows]
