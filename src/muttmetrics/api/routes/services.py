"""Service catalog - list packages for capture."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from muttmetrics.api.deps import get_db, require_api_key
from muttmetrics.api.schemas.services import ServiceListItem
from muttmetrics.models.service import Service

router = APIRouter(tags=["services"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/services", dependencies=[Depends(require_api_key)])
def list_services(session: DbSession) -> list[ServiceListItem]:
    """Return the seeded service catalog for the SPA picker."""
    rows = session.scalars(
        select(Service).order_by(Service.base_minutes.nulls_last(), Service.service_id)
    ).all()
    return [ServiceListItem.model_validate(row) for row in rows]
