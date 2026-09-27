"""Photo upload and serving. Bytes on disk, metadata in Postgres."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from muttmetrics import images, storage
from muttmetrics.api.deps import get_db, require_api_key
from muttmetrics.api.schemas.photos import PhotoResponse
from muttmetrics.models import Photo, Visit

router = APIRouter(tags=["photos"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/visits/{visit_id}/photos",
    status_code=201,
    dependencies=[Depends(require_api_key)],
)
def upload_visit_photo(
    visit_id: int,
    session: DbSession,
    file: Annotated[UploadFile, File()],
    kind: Annotated[Literal["intake", "after"], Form()] = "intake",
) -> PhotoResponse:
    """Store one photo for a visit: validate, strip metadata, save."""
    visit = session.get(Visit, visit_id)
    if visit is None:
        raise HTTPException(status_code=404, detail=f"Visit {visit_id} not found")

    raw = file.file.read()
    try:
        processed = images.process_upload(raw)
    except images.ImageTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except images.ImageRejected as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    key = storage.build_key()
    storage.write_bytes(key, processed)

    photo = Photo(
        dog_id=visit.dog_id,
        visit_id=visit.visit_id,
        kind=kind,
        storage_key=key,
        content_type="image/jpeg",
        byte_size=len(processed),
        sha256=storage.sha256_of(processed),
    )
    try:
        session.add(photo)
        session.flush()
    except Exception:
        # The row never landed, so nothing points at these bytes. Best effort -
        # the sweeper would catch it anyway, and a failure here must not hide
        # the real error
        try:
            storage.delete(key)
        except OSError:
            pass
        raise

    return PhotoResponse.model_validate(photo)


@router.get("/visits/{visit_id}/photos", dependencies=[Depends(require_api_key)])
def list_visit_photos(visit_id: int, session: DbSession) -> list[PhotoResponse]:
    """Metadata for every photo on a visit, oldest first."""
    if session.get(Visit, visit_id) is None:
        raise HTTPException(status_code=404, detail=f"Visit {visit_id} not found")

    rows = session.scalars(
        select(Photo).where(Photo.visit_id == visit_id).order_by(Photo.photo_id)
    ).all()
    return [PhotoResponse.model_validate(row) for row in rows]


@router.get("/photos/{photo_id}", dependencies=[Depends(require_api_key)])
def get_photo(photo_id: int, session: DbSession) -> Response:
    """The bytes. Auth means an <img src> cannot fetch this directly."""
    photo = session.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail=f"Photo {photo_id} not found")

    try:
        data = storage.read_bytes(photo.storage_key)
    except FileNotFoundError as exc:
        # Row promises bytes that are gone - the inconsistency designed
        # the write order to avoid. 404 for the caller; the row is the clue
        raise HTTPException(status_code=404, detail=f"Photo {photo_id} file is missing") from exc

    return Response(
        content=data,
        media_type=photo.content_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )
