"""Sebastian-facing capture pages (HTML), not the JSON API."""

from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from muttmetrics.api.deps import get_db
from muttmetrics.api.services.dogs import create_or_get_dog
from muttmetrics.api.services.owners import create_or_get_owner
from muttmetrics.models import Visit

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["capture"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/capture")
def capture_form(request: Request):
    """Serve the post-groom HTML form."""
    return templates.TemplateResponse(
        request=request,
        name="capture.html",
        context={"heading": "MuttMetrics Capture"},
    )


@router.post("/capture")
def capture_submit(
    request: Request,
    session: DbSession,
    owner_name: Annotated[str, Form()],
    dog_name: Annotated[str, Form()],
    visit_date: Annotated[date, Form()],
    actual_minutes: Annotated[int, Form()],
    condition_score: Annotated[str, Form()] = "",
    what_surprised_me: Annotated[str, Form()] = "",
):
    """Create-or-get owner/dog, then insert a visit row."""
    score = int(condition_score) if condition_score.strip() else None
    surprise = what_surprised_me.strip() or None

    try:
        owner, _ = create_or_get_owner(session, name=owner_name)
        dog, _ = create_or_get_dog(
            session,
            owner_id=owner.owner_id,
            name=dog_name,
        )
        visit = Visit(
            dog_id=dog.dog_id,
            owner_id=owner.owner_id,
            visit_date=visit_date,
            actual_minutes=actual_minutes,
            condition_score=score,
            what_surprised_me=surprise,
            status="completed",
        )
        session.add(visit)
        session.flush()
    except ValueError as exc:
        return templates.TemplateResponse(
            request=request,
            name="capture.html",
            context={
                "heading": "MuttMetrics Capture",
                "error": str(exc),
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="capture_success.html",
        context={"visit_id": visit.visit_id},
    )
