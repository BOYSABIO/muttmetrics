"""Pet create-or-get, search, and Directory profile reads."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from muttmetrics.api.schemas.pets import (
    OwnerSummary,
    PatchPetRequest,
    PetProfile,
    PetSearchItem,
)
from muttmetrics.api.services.patching import reject_null_for_required_columns
from muttmetrics.api.services.visits import visit_to_summary
from muttmetrics.models import Breed, Owner, Pet, PetChange, Photo, Visit, VisitAddOn
from muttmetrics.pet_vocab import COAT_TYPES_BY_SPECIES, TRACKED_PET_FIELDS
from muttmetrics.priors.size import size_band_from_weight
from muttmetrics.services.visit_eligibility import visit_counts_clause
from muttmetrics.species import ALLOWED_SPECIES, DEFAULT_SPECIES


def normalize_pet_name(name: str) -> str:
    """Collapse whitespace; keep casing for storage."""
    return " ".join(name.split())


def ensure_breed_matches_species(
    session: Session,
    breed_id: int | None,
    species: str,
) -> None:
    """Raise LookupError if missing, ValueError if species mismatch."""
    if breed_id is None:
        return
    breed = session.get(Breed, breed_id)
    if breed is None:
        raise LookupError(f"Breed {breed_id} not found")
    if breed.species != species:
        raise ValueError(f"Breed {breed_id} is species {breed.species!r}, pet is {species!r}")


def create_or_get_pet(
    session: Session,
    *,
    owner_id: int,
    name: str,
    species: str = DEFAULT_SPECIES,
    breed_id: int | None = None,
) -> tuple[Pet, bool]:
    """
    Return (pet, created). Match is owner + name + species.

    Raises ValueError for blank name or breed/species mismatch.
    Raises LookupError with a clear message if owner (or breed) missing -
    the route turns those into 404.
    """
    cleaned = normalize_pet_name(name)
    if not cleaned:
        raise ValueError("Pet name must not be empty")
    if species not in ALLOWED_SPECIES:
        raise ValueError(f"species must be one of {ALLOWED_SPECIES}")

    if session.get(Owner, owner_id) is None:
        raise LookupError(f"Owner {owner_id} not found")

    ensure_breed_matches_species(session, breed_id, species)

    existing = session.scalar(
        select(Pet).where(
            Pet.owner_id == owner_id,
            func.lower(Pet.name) == cleaned.lower(),
            Pet.species == species,
        )
    )
    if existing is not None:
        return existing, False

    pet = Pet(owner_id=owner_id, name=cleaned, species=species, breed_id=breed_id)
    session.add(pet)
    session.flush()
    return pet, True


def search_pets(
    session: Session,
    *,
    q: str | None = None,
    limit: int = 50,
) -> list[PetSearchItem]:
    """
    Directory list: pets with owner display name.

    Empty / blank q -> up to `limit` pets (browse).
    Non-empty q -> pet.name ILIKE %q% (case-insensitive).
    last_visit_date is live from visit rows (eligible statuses only), not the
    stored pet.last_visit_date column (#171)
    """
    last_visit_sq = (
        select(
            Visit.pet_id.label("pet_id"),
            func.max(Visit.visit_date).label("last_visit_date"),
        )
        .where(visit_counts_clause())
        .group_by(Visit.pet_id)
        .subquery()
    )

    stmt = (
        select(Pet, last_visit_sq.c.last_visit_date)
        .options(joinedload(Pet.owner))
        .outerjoin(last_visit_sq, Pet.pet_id == last_visit_sq.c.pet_id)
        .order_by(Pet.name)
        .limit(limit)
    )
    cleaned = (q or "").strip()
    if cleaned:
        # Escape LIKE wildcards so "%" or "_" in a search match literally (#180).
        literal = cleaned.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(Pet.name.ilike(f"%{literal}%", escape="\\"))

    rows = session.execute(stmt).unique().all()
    return [
        PetSearchItem(
            pet_id=pet.pet_id,
            name=pet.name,
            species=pet.species,  # type: ignore[arg-type]
            owner_id=pet.owner_id,
            owner_name=pet.owner.name,
            last_visit_date=last_visit_date,
        )
        for pet, last_visit_date in rows
    ]


def get_pet_profile(
    session: Session,
    *,
    pet_id: int,
    recent_limit: int = 10,
) -> PetProfile:
    """
    Load one pet for Directory: hand-entered fields, owner stub, recent visits.

    Raises LookupError if pet_id missing (route -> 404).
    """
    pet = session.scalar(select(Pet).options(joinedload(Pet.owner)).where(Pet.pet_id == pet_id))
    if pet is None:
        raise LookupError(f"Pet {pet_id} not found")

    limit = max(0, min(recent_limit, 50))
    visits = session.scalars(
        select(Visit)
        .options(selectinload(Visit.visit_add_ons).selectinload(VisitAddOn.add_on))
        .where(Visit.pet_id == pet_id)
        .order_by(Visit.visit_date.desc(), Visit.visit_id.desc())
        .limit(limit)
    ).all()

    # Live count from visit rows — derived pet.visit_count can lag / be null
    # when recompute hasn't run (Directory should still show the truth).
    visit_count = session.scalar(
        select(func.count()).select_from(Visit).where(Visit.pet_id == pet_id, visit_counts_clause())
    )
    last_visit_date = session.scalar(
        select(func.max(Visit.visit_date)).where(
            Visit.pet_id == pet_id,
            visit_counts_clause(),
        )
    )

    avatar_photo_id = session.scalar(
        select(Photo.photo_id)
        .where(Photo.pet_id == pet_id, Photo.kind == "profile")
        .order_by(Photo.photo_id.desc())
        .limit(1)
    )
    if avatar_photo_id is None:
        avatar_photo_id = session.scalar(
            select(Photo.photo_id)
            .where(Photo.pet_id == pet_id, Photo.kind == "intake")
            .order_by(Photo.photo_id.desc())
            .limit(1)
        )

    profile = PetProfile.model_validate(pet)
    return profile.model_copy(
        update={
            "owner": OwnerSummary.model_validate(pet.owner),
            "recent_visits": [visit_to_summary(v) for v in visits],
            "avatar_photo_id": avatar_photo_id,
            "visit_count": int(visit_count or 0),
            "last_visit_date": last_visit_date,
        }
    )


def _as_text(value: object) -> str | None:
    """Change-log spelling: NULL stays NULL; bools lower-case; numbers plain."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    return str(value)


def _apply_size(pet: Pet, updates: dict) -> None:
    """Size rules (docs/architecture/pet-data.md).

    A weighed pet's size comes from its weight (source 'weight'); a size sent
    alongside a weight is ignored. Without a weight, the size is the one picked
    by eye (source 'eye'). Clearing the weight of a pet whose size came from
    it leaves the size blank, since nobody has picked one.
    """
    weight = float(pet.weight_kg) if pet.weight_kg is not None else None
    from_weight = size_band_from_weight(weight, pet.species)
    if from_weight is not None:
        pet.size_band, pet.size_source = from_weight, "weight"
    elif "size_band" in updates:
        picked = updates["size_band"]
        pet.size_band, pet.size_source = picked, ("eye" if picked else None)
    elif pet.size_source == "weight":
        pet.size_band, pet.size_source = None, None


def patch_pet(
    session: Session,
    *,
    pet_id: int,
    body: PatchPetRequest,
) -> PetProfile:
    """
    Apply a partial pet update. Only fields present in the JSON are touched,
    so a field the client didn't send keeps its value (blank stays blank).

    Every tracked field that actually changed gets a pet_change row.

    Raises LookupError if pet or breed id missing
    Raises ValueError if name is sent but blank, breed/species mismatch, or a
    coat type that isn't on the list for the pet's species.
    """
    pet = session.get(Pet, pet_id)

    if pet is None:
        raise LookupError(f"Pet {pet_id} not found")

    updates = body.model_dump(exclude_unset=True)
    reject_null_for_required_columns(Pet, updates)

    if "name" in updates:
        cleaned = normalize_pet_name(updates["name"] or "")
        if not cleaned:
            raise ValueError("Pet name must not be empty")
        updates["name"] = cleaned

    if "species" in updates and updates["species"] not in ALLOWED_SPECIES:
        raise ValueError(f"species must be one of {ALLOWED_SPECIES}")

    new_species = updates.get("species", pet.species)
    for breed_key in ("breed_id", "breed_secondary_id"):
        breed_id = updates[breed_key] if breed_key in updates else getattr(pet, breed_key)
        ensure_breed_matches_species(session, breed_id, new_species)

    allowed_coats = COAT_TYPES_BY_SPECIES.get(new_species, ())
    if "coat_type" in updates:
        if updates["coat_type"] is not None and updates["coat_type"] not in allowed_coats:
            raise ValueError(
                f"coat_type {updates['coat_type']!r} is not a {new_species} coat; "
                f"use one of {allowed_coats}"
            )
    elif pet.coat_type is not None and pet.coat_type not in allowed_coats:
        # Species changed and the old coat doesn't exist for the new one.
        updates["coat_type"] = None

    before = {field: getattr(pet, field) for field in TRACKED_PET_FIELDS}

    for key, value in updates.items():
        if key == "size_band":
            continue  # _apply_size decides
        setattr(pet, key, value)
    _apply_size(pet, updates)

    for field in TRACKED_PET_FIELDS:
        old, new = _as_text(before[field]), _as_text(getattr(pet, field))
        if old != new:
            session.add(PetChange(pet_id=pet.pet_id, field=field, old_value=old, new_value=new))

    session.flush()
    return get_pet_profile(session, pet_id=pet_id)
