"""Visit capture routes — create a visit row in Postgres."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from muttmetrics.api.deps import get_db, require_api_key
from muttmetrics.api.schemas.visits import (
    CreateVisitRequest,
    PatchVisitRequest,
    VisitResponse,
)
from muttmetrics.api.services.visits import (
    delete_visit,
    load_visit,
    patch_visit,
    set_visit_add_ons,
    visit_to_response,
)
from muttmetrics.models import Dog, Owner, Service, Visit
from muttmetrics.services.visit_predictions import compute_visit_predictions

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

    dog = session.get(Dog, body.dog_id)
    if dog is None:
        raise HTTPException(status_code=404, detail=f"Dog {body.dog_id} not found")

    # Both rows exist, but do they belong together? A mismatch would credit
    # this groom to the wrong owner's history.
    if dog.owner_id != body.owner_id:
        raise HTTPException(
            status_code=422,
            detail=f"Dog {body.dog_id} belongs to owner {dog.owner_id}, not {body.owner_id}",
        )

    # Same rule as owner/dog/breed: a referenced id that doesn't exist is a 404,
    # caught here instead of as an IntegrityError (500) at flush time.
    for service_id in {body.booked_service_id, body.actual_service_id} - {None}:
        if session.get(Service, service_id) is None:
            raise HTTPException(status_code=404, detail=f"Service {service_id} not found")

    days_since_last, p50, p90 = compute_visit_predictions(
        session, dog=dog, visit_date=body.visit_date
    )

    visit = Visit(
        dog_id=body.dog_id,
        owner_id=body.owner_id,
        visit_date=body.visit_date,
        actual_minutes=body.actual_minutes,
        condition_score=body.condition_score,
        booked_service_id=body.booked_service_id,
        actual_service_id=body.actual_service_id,
        what_surprised_me=body.what_surprised_me,
        quoted_price=body.quoted_price,
        final_price=body.final_price,
        tip=body.tip,
        shaved_down=body.shaved_down,
        status=body.status,
        days_since_last=days_since_last,
        predicted_min_p50=p50,
        predicted_min_p90=p90,
    )
    session.add(visit)
    session.flush()

    try:
        set_visit_add_ons(session, visit, body.add_on_ids)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    session.flush()
    reloaded = load_visit(session, visit.visit_id)
    assert reloaded is not None
    return visit_to_response(reloaded)


@router.get(
    "/visits/{visit_id}",
    dependencies=[Depends(require_api_key)],
)
def read_visit(visit_id: int, session: DbSession) -> VisitResponse:
    """Load one visit for Directory edit (#193)."""
    visit = load_visit(session, visit_id)
    if visit is None:
        raise HTTPException(status_code=404, detail=f"Visit {visit_id} not found")
    return visit_to_response(visit)


@router.patch(
    "/visits/{visit_id}",
    dependencies=[Depends(require_api_key)],
)
def update_visit(
    visit_id: int,
    body: PatchVisitRequest,
    session: DbSession,
) -> VisitResponse:
    """Partial update of event facts; system-computed columns stay server-owned."""
    try:
        return patch_visit(session, visit_id=visit_id, body=body)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete(
    "/visits/{visit_id}",
    status_code=204,
    dependencies=[Depends(require_api_key)],
)
def remove_visit(visit_id: int, session: DbSession) -> Response:
    """Hard-delete a visit + its photos. Mistakes are recovered from backups."""
    try:
        delete_visit(session, visit_id=visit_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return Response(status_code=204)
