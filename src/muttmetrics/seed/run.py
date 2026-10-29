"""Upsert breed, service, and add-on reference rows; print acceptance queries."""

from sqlalchemy import func, select

from muttmetrics.db.session import session_scope
from muttmetrics.models import AddOn, Breed, Service
from muttmetrics.seed.data import SEED_ADD_ONS, SEED_BREEDS, SEED_SERVICES
from muttmetrics.seed.pricing import apply_price_overrides, load_price_overrides


def _upsert_service(session, row: dict) -> None:
    existing = session.scalar(select(Service).where(Service.slug == row["slug"]))
    if existing is None:
        session.add(Service(**row))
        return
    for key, value in row.items():
        if key == "slug":
            continue
        setattr(existing, key, value)


def _upsert_add_on(session, row: dict) -> None:
    existing = session.scalar(select(AddOn).where(AddOn.slug == row["slug"]))
    if existing is None:
        session.add(AddOn(**row))
        return
    for key, value in row.items():
        if key == "slug":
            continue
        setattr(existing, key, value)


def _upsert_breed(session, row: dict) -> None:
    existing = session.scalar(select(Breed).where(Breed.name_en == row["name_en"]))
    if existing is None:
        session.add(Breed(**row))
        return
    for key, value in row.items():
        if key == "name_en":
            continue
        setattr(existing, key, value)


def seed_reference_data() -> None:
    """Upsert seed services, add-ons, and breeds; print acceptance query results."""
    overrides = load_price_overrides()
    services = apply_price_overrides(SEED_SERVICES, overrides)
    add_ons = apply_price_overrides(SEED_ADD_ONS, overrides)
    with session_scope() as session:
        for row in services:
            _upsert_service(session, row)
        for row in add_ons:
            _upsert_add_on(session, row)
        for row in SEED_BREEDS:
            _upsert_breed(session, row)

        n_services = session.scalar(select(func.count()).select_from(Service)) or 0
        n_add_ons = session.scalar(select(func.count()).select_from(AddOn)) or 0
        n_breeds = session.scalar(select(func.count()).select_from(Breed)) or 0
        high_mat = session.scalars(
            select(Breed)
            .where(Breed.matting_risk >= 4)
            .order_by(Breed.matting_risk.desc(), Breed.name_en)
        ).all()

        print(f"Seeded services: {n_services}")
        print(f"Seeded add-ons: {n_add_ons}")
        print(f"Seeded breeds: {n_breeds}")
        print(f"Breeds with matting_risk >= 4 ({len(high_mat)}):")
        for breed in high_mat:
            print(f"  - {breed.name_en} (risk={breed.matting_risk})")
