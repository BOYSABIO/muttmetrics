"""Visit patch (and later delete) - event facts only."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from muttmetrics.api.schemas.visits import PatchVisitRequest, VisitResponse
from muttmetrics.api.services.patching import reject_null_for_required_columns
from muttmetrics.media import storage
from muttmetrics.models import Dog, Photo, Service, Visit
from muttmetrics.services.visit_predictions import _days_since_last


def patch_visit(
    session: Session,
    *,
    visit_id: int,
    body: PatchVisitRequest,
) -> VisitResponse:
    """Apply a partial visit update. Raises LookupError / ValueError for the route."""
    visit = session.get(Visit, visit_id)
    if visit is None:
        raise LookupError(f"Visit {visit_id} not found")

    updates = body.model_dump(exclude_unset=True)
    reject_null_for_required_columns(Visit, updates)

    for service_key in ("booked_service_id", "actual_service_id"):
        if service_key in updates and updates[service_key] is not None:
            if session.get(Service, updates[service_key]) is None:
                raise LookupError(f"Service {updates[service_key]} not found")

    for key, value in updates.items():
        setattr(visit, key, value)

    # Date changed -> gap is a fact about the new date; predictions stay frozen
    if "visit_date" in updates:
        dog = session.get(Dog, visit.dog_id)
        if dog is None:
            raise LookupError(f"Dog {visit.dog_id} not found")
        visit.days_since_last = _days_since_last(
            session,
            dog_id=dog.dog_id,
            visit_date=visit.visit_date,
            exclude_visit_id=visit.visit_id,
        )

    session.flush()
    return VisitResponse.model_validate(visit)


def delete_visit(session: Session, *, visit_id: int) -> None:
    """Hard-delete a visit and it's photos (files, then rows). Raises LookupError."""
    visit = session.get(Visit, visit_id)
    if visit is None:
        raise LookupError(f"Visit {visit_id} not found")

    photos = list(session.scalars(select(Photo).where(Photo.visit_id == visit_id)).all())

    # Files first - fail before any DB deletes if disk refuses
    for photo in photos:
        try:
            storage.delete(photo.storage_key)
        except (OSError, ValueError) as exc:
            raise RuntimeError(
                f"Could not delete photo file for photo_id={photo.photo_id}: {exc}"
            ) from exc

    # Phot rows, then the visit
    for photo in photos:
        session.delete(photo)
    session.delete(visit)
    session.flush()
