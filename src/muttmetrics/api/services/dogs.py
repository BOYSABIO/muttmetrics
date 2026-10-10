"""Dog create-or-get, search, and Directory profile reads."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from muttmetrics.api.schemas.dogs import (
    DogProfile,
    DogSearchItem,
    OwnerSummary,
    PatchDogRequest,
    VisitSummary,
)
from muttmetrics.models import Breed, Dog, Owner, Photo, Visit


def normalize_dog_name(name: str) -> str:
    """Collapse whitespace; keep casing for storage."""
    return " ".join(name.split())


def create_or_get_dog(
    session: Session,
    *,
    owner_id: int,
    name: str,
    breed_id: int | None = None,
) -> tuple[Dog, bool]:
    """
    Return (dog, created).

    Raises ValueError for blank name.
    Raises LookupError with a clear message if owner (or breed) missing -
    the route turns those into 404.
    """
    cleaned = normalize_dog_name(name)
    if not cleaned:
        raise ValueError("Dog name must not be empty")

    if session.get(Owner, owner_id) is None:
        raise LookupError(f"Owner {owner_id} not found")

    if breed_id is not None and session.get(Breed, breed_id) is None:
        raise LookupError(f"Breed {breed_id} not found")

    existing = session.scalar(
        select(Dog).where(
            Dog.owner_id == owner_id,
            func.lower(Dog.name) == cleaned.lower(),
        )
    )
    if existing is not None:
        return existing, False

    dog = Dog(owner_id=owner_id, name=cleaned, breed_id=breed_id)
    session.add(dog)
    session.flush()
    return dog, True


def search_dogs(
    session: Session,
    *,
    q: str | None = None,
    limit: int = 50,
) -> list[DogSearchItem]:
    """
    Directory list: dogs with owner display name.

    Empty / blank q -> up to `limit` dogs (browse).
    Non-empty q -> dog.name ILIKE %q% (case-insensitive).
    """
    stmt = select(Dog).options(joinedload(Dog.owner)).order_by(Dog.name).limit(limit)
    cleaned = (q or "").strip()
    if cleaned:
        stmt = stmt.where(Dog.name.ilike(f"%{cleaned}%"))

    dogs = session.scalars(stmt).unique().all()
    return [
        DogSearchItem(
            dog_id=dog.dog_id,
            name=dog.name,
            owner_id=dog.owner_id,
            owner_name=dog.owner.name,
            last_visit_date=dog.last_visit_date,
        )
        for dog in dogs
    ]


def get_dog_profile(
    session: Session,
    *,
    dog_id: int,
    recent_limit: int = 10,
) -> DogProfile:
    """
    Load one dog for Directory: hand-entered fields, owner stub, recent visits.

    Raises LookupError if dog_id missing (route -> 404).
    """
    dog = session.scalar(select(Dog).options(joinedload(Dog.owner)).where(Dog.dog_id == dog_id))
    if dog is None:
        raise LookupError(f"Dog {dog_id} not found")

    limit = max(0, min(recent_limit, 50))
    visits = session.scalars(
        select(Visit)
        .where(Visit.dog_id == dog_id)
        .order_by(Visit.visit_date.desc(), Visit.visit_id.desc())
        .limit(limit)
    ).all()

    # Live count from visit rows — derived dog.visit_count can lag / be null
    # when recompute hasn't run (Directory should still show the truth).
    visit_count = session.scalar(
        select(func.count()).select_from(Visit).where(Visit.dog_id == dog_id)
    )
    last_visit_date = session.scalar(
        select(func.max(Visit.visit_date)).where(Visit.dog_id == dog_id)
    )

    avatar_photo_id = session.scalar(
        select(Photo.photo_id)
        .where(Photo.dog_id == dog_id, Photo.kind == "profile")
        .order_by(Photo.photo_id.desc())
        .limit(1)
    )
    if avatar_photo_id is None:
        avatar_photo_id = session.scalar(
            select(Photo.photo_id)
            .where(Photo.dog_id == dog_id, Photo.kind == "intake")
            .order_by(Photo.photo_id.desc())
            .limit(1)
        )

    profile = DogProfile.model_validate(dog)
    return profile.model_copy(
        update={
            "owner": OwnerSummary.model_validate(dog.owner),
            "recent_visits": [VisitSummary.model_validate(v) for v in visits],
            "avatar_photo_id": avatar_photo_id,
            "visit_count": int(visit_count or 0),
            "last_visit_date": last_visit_date,
        }
    )


def patch_dog(
    session: Session,
    *,
    dog_id: int,
    body: PatchDogRequest,
) -> DogProfile:
    """
    Apply a partial dog update. Only fields present in the JSON are touched.

    Raises LookupError if dog or breed id missing
    Raises ValueError if name is sent but blank.
    """
    dog = session.get(Dog, dog_id)

    if dog is None:
        raise LookupError(f"Dog {dog_id} not found")

    updates = body.model_dump(exclude_unset=True)

    if "name" in updates:
        cleaned = normalize_dog_name(updates["name"] or "")
        if not cleaned:
            raise ValueError("Dog name must not be empty")
        updates["name"] = cleaned

    for breed_key in ("breed_id", "breed_secondary_id"):
        if breed_key in updates and updates[breed_key] is not None:
            if session.get(Breed, updates[breed_key]) is None:
                raise LookupError(f"Breed {updates[breed_key]} not found")

    for key, value in updates.items():
        setattr(dog, key, value)

    session.flush()
    return get_dog_profile(session, dog_id=dog_id)
