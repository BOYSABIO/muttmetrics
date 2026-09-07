"""Visit capture routes — create a visit row in Postgres."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from muttmetrics.api.deps import get_db, require_api_key
from muttmetrics.api.schemas.visits import CreateVisitRequest, VisitResponse
from muttmetrics.models import Dog, Owner, Visit

router = APIRouter(tags=["visits"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/visits",
    status_code=201,
    dependencies=[Depends(require_api_key)],
)
def create_visit(body: CreateVisitRequest, session: DbSession) -> VisitResponse:
    """Persist a post-groom visit; dog and owner must already exist."""
    if session.get(Owner, body.owner_id) is None:
        raise HTTPException(status_code=404, detail=f"Owner {body.owner_id} not found")
    if session.get(Dog, body.dog_id) is None:
        raise HTTPException(status_code=404, detail=f"Dog {body.dog_id} not found")

    visit = Visit(
        dog_id=body.dog_id,
        owner_id=body.owner_id,
        visit_date=body.visit_date,
        actual_minutes=body.actual_minutes,
        condition_score=body.condition_score,
        booked_service_id=body.booked_service_id,
        actual_service_id=body.actual_service_id,
        what_surprised_me=body.what_surprised_me,
        intake_photos=body.intake_photos,
        after_photos=body.after_photos,
        quoted_price=body.quoted_price,
        final_price=body.final_price,
        tip=body.tip,
        status=body.status,
    )
    session.add(visit)
    session.flush()
    return VisitResponse.model_validate(visit)
