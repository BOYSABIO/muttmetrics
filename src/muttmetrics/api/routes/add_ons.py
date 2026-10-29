"""Add-on catalog — list techniques for capture (#192)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from muttmetrics.api.deps import get_db, require_api_key
from muttmetrics.api.schemas.add_ons import AddOnListItem
from muttmetrics.models import AddOn

router = APIRouter(tags=["add-ons"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/add-ons", dependencies=[Depends(require_api_key)])
def list_add_ons(session: DbSession) -> list[AddOnListItem]:
    """Return the seeded add-on catalog for the SPA picker."""
    rows = session.scalars(select(AddOn).order_by(AddOn.add_on_id)).all()
    return [AddOnListItem.model_validate(row) for row in rows]
