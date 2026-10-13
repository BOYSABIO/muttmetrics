"""Load the synthetic metric-week rows into a Session (#16).

Caller owns the transaction (tests: db_session rollback; CLI: its own commit).
"""

from __future__ import annotations

from sqlalchemy.orm import Session
from tests.fixtures.metric_week import DOGS, OWNERS, VISITS

from muttmetrics.models import Breed, Dog, Owner, Visit


def load_metric_week(session: Session) -> dict[str, dict[str, int]]:
    """Insert Syn* breeds/owners/dogs/visits. Returns id maps by recipe key."""
    breed_ids: dict[str, int] = {}
    owner_ids: dict[str, int] = {}
    dog_ids: dict[str, int] = {}
    # dog_key → owner_key (avoids a lookup loop when inserting visits)
    dog_owner_key = {d["key"]: d["owner_key"] for d in DOGS}

    # --- breeds (one per distinct breed_en on DOGS) ---
    for breed_en in {d["breed_en"] for d in DOGS}:
        breed = Breed(
            name_en=breed_en,
            name_de=breed_en,
            base_groom_minutes=60,
            matting_risk=3,
            recommended_interval_days=60,
        )
        session.add(breed)
        session.flush()
        breed_ids[breed_en] = breed.breed_id

    # --- owners ---
    for spec in OWNERS:
        owner = Owner(name=spec["name"])
        session.add(owner)
        session.flush()
        owner_ids[spec["key"]] = owner.owner_id

    # --- dogs ---
    for spec in DOGS:
        dog = Dog(
            name=spec["name"],
            owner_id=owner_ids[spec["owner_key"]],
            breed_id=breed_ids[spec["breed_en"]],
        )
        session.add(dog)
        session.flush()
        dog_ids[spec["key"]] = dog.dog_id

    # --- visits ---
    for spec in VISITS:
        visit = Visit(
            dog_id=dog_ids[spec["dog_key"]],
            owner_id=owner_ids[dog_owner_key[spec["dog_key"]]],
            visit_date=spec["visit_date"],
            status=spec["status"],
            condition_score=spec["condition_score"],
            shaved_down=spec["shaved_down"],
            pivoted=spec["pivoted"],
            actual_minutes=spec["actual_minutes"],
            predicted_min_p50=spec["predicted_min_p50"],
            predicted_min_p90=spec["predicted_min_p90"],
            final_price=spec["final_price"],
            tip=spec["tip"],
        )
        session.add(visit)

    session.flush()
    return {"breed_ids": breed_ids, "owner_ids": owner_ids, "dog_ids": dog_ids}
