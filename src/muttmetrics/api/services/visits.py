"""Visit patch/delete + add-on join helpers (#192)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from muttmetrics.api.schemas.add_ons import AddOnSummary
from muttmetrics.api.schemas.dogs import VisitSummary
from muttmetrics.api.schemas.visits import PatchVisitRequest, VisitResponse
from muttmetrics.api.services.patching import reject_null_for_required_columns
from muttmetrics.media import storage
from muttmetrics.models import AddOn, Dog, Photo, Service, Visit, VisitAddOn
from muttmetrics.services.visit_predictions import _days_since_last


def _add_on_summaries(visit: Visit) -> list[AddOnSummary]:
    return [
        AddOnSummary.model_validate(link.add_on)
        for link in visit.visit_add_ons
        if link.add_on is not None
    ]


def visit_to_response(visit: Visit) -> VisitResponse:
    """Map a Visit ORM row (with add-ons loaded) to the API response."""
    base = VisitResponse.model_validate(visit)
    return base.model_copy(update={"add_ons": _add_on_summaries(visit)})


def visit_to_summary(visit: Visit) -> VisitSummary:
    """Map a Visit ORM row to a dog-profile recent-visit row."""
    base = VisitSummary.model_validate(visit)
    return base.model_copy(update={"add_ons": _add_on_summaries(visit)})


def load_visit(session: Session, visit_id: int) -> Visit | None:
    """Load one visit with add-on links + catalog rows."""
    return session.scalar(
        select(Visit)
        .options(selectinload(Visit.visit_add_ons).selectinload(VisitAddOn.add_on))
        .where(Visit.visit_id == visit_id)
    )


def set_visit_add_ons(session: Session, visit: Visit, add_on_ids: list[int]) -> None:
    """
    Replace visit_add_on rows for this visit.

    Raises LookupError if any id is missing from the catalog (route → 404).
    """
    ids = list(dict.fromkeys(add_on_ids))
    for add_on_id in ids:
        if session.get(AddOn, add_on_id) is None:
            raise LookupError(f"Add-on {add_on_id} not found")

    visit.visit_add_ons.clear()
    for add_on_id in ids:
        visit.visit_add_ons.append(VisitAddOn(add_on_id=add_on_id))


def patch_visit(
    session: Session,
    *,
    visit_id: int,
    body: PatchVisitRequest,
) -> VisitResponse:
    """Apply a partial visit update. Raises LookupError / ValueError for the route."""
    visit = load_visit(session, visit_id)
    if visit is None:
        raise LookupError(f"Visit {visit_id} not found")

    updates = body.model_dump(exclude_unset=True)
    add_on_ids = updates.pop("add_on_ids", None)
    reject_null_for_required_columns(Visit, updates)

    for service_key in ("booked_service_id", "actual_service_id"):
        if service_key in updates and updates[service_key] is not None:
            if session.get(Service, updates[service_key]) is None:
                raise LookupError(f"Service {updates[service_key]} not found")

    for key, value in updates.items():
        setattr(visit, key, value)

    if add_on_ids is not None:
        set_visit_add_ons(session, visit, add_on_ids)

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
    reloaded = load_visit(session, visit.visit_id)
    assert reloaded is not None
    return visit_to_response(reloaded)


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
