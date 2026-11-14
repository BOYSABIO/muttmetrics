"""Rolling synthetic visits for the last few weeks, so the dashboard has
something to show *today* (for UI work, screenshots and video footage).

Used by ``python ops/demo_data.py --recent``; the same empty-database rule
applies. Everything is invented: Syn* names, made-up prices (never the real
ones in data/private/pricing.json), and a fixed random seed, so two runs on
the same day produce the same rows.

What it's built to show:
  - repeat visits, so "this dog last time" and the timing numbers have history
  - two owners with two dogs groomed back to back, and a couple of cats
  - bad coats taking longer without being charged in proportion (the
    "inverted incentive" the € / hour by coat card exists for)
  - add-ons, tips, and dog profiles that are only partly filled in
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from muttmetrics.models import AddOn, Breed, Owner, Pet, Service, Visit, VisitAddOn
from muttmetrics.pet_vocab import COAT_TYPES_BY_SPECIES
from muttmetrics.priors.size import size_band_from_weight
from muttmetrics.services.visit_predictions import compute_visit_predictions

WEEKS = 12
SEED = 20261114

# Invented names; "Syn" marks every row as synthetic (same rule as tests/fixtures).
DOG_NAMES = [
    "Biscuit",
    "Pepper",
    "Noodle",
    "Mochi",
    "Waffles",
    "Juniper",
    "Pickles",
    "Toffee",
    "Bean",
    "Clover",
    "Ziggy",
    "Maple",
    "Otis",
    "Pretzel",
    "Luna",
    "Taco",
    "Sprout",
    "Hazel",
    "Nacho",
    "Pumpkin",
    "Basil",
    "Olive",
    "Dumpling",
    "Rolo",
    "Fig",
    "Chai",
    "Gizmo",
    "Muffin",
    "Sage",
    "Tofu",
    "Bagel",
    "Kiwi",
]
CAT_NAMES = ["Miso", "Pixel"]


@dataclass
class _Dog:
    pet: Pet
    base: int  # typical minutes for this animal, before the coat's condition
    interval: int  # days between visits
    usual_condition: int


def _work_days(start: date, end: date) -> list[date]:
    """Tuesday–Saturday, the salon's days (weekday 1..5)."""
    days = []
    d = start
    while d <= end:
        if 1 <= d.weekday() <= 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def _service_for(species: str, base: int, services: dict[str, Service]) -> Service:
    """A full groom for bigger jobs, a bath & trim otherwise; only ones offered for the species."""
    offered = [s for s in services.values() if s.species in (None, species)]
    preferred = "full_groom" if base >= 60 else "bath_trim"
    for s in offered:
        if s.slug == preferred:
            return s
    return offered[0] if offered else services["full_groom"]


def _round5(x: float) -> int:
    return max(15, int(round(x / 5.0)) * 5)


def load_recent(session: Session, today: date | None = None) -> int:
    """Insert ~WEEKS weeks of synthetic history ending today. Returns visits added.

    Needs the seeded catalog (breeds, services, add-ons): run the seed first.
    """
    today = today or date.today()
    rng = random.Random(SEED)

    dog_breeds = list(session.scalars(select(Breed).where(Breed.species == "dog")))
    cat_breeds = list(session.scalars(select(Breed).where(Breed.species == "cat")))
    services = {s.slug: s for s in session.scalars(select(Service))}
    add_ons = {a.slug: a for a in session.scalars(select(AddOn))}
    real_dog_breeds = [
        b for b in dog_breeds if b.base_groom_minutes and not (b.name_en or "").startswith("Syn")
    ]
    if not real_dog_breeds or "full_groom" not in services:
        raise RuntimeError(
            "Run the seed first: the recent demo needs the breed and service catalog."
        )

    start = today - timedelta(weeks=WEEKS)
    days = _work_days(start, today)

    # --- owners and animals ---------------------------------------------------
    dogs: list[_Dog] = []

    def make_animal(owner: Owner, name: str, species: str) -> _Dog:
        breed = rng.choice(real_dog_breeds if species == "dog" else (cat_breeds or real_dog_breeds))
        weight = round(rng.uniform(3.5, 6.0) if species == "cat" else rng.uniform(4, 35), 1)
        # Profiles are deliberately incomplete, like the real ones in the shop.
        filled = rng.random() < 0.6
        pet = Pet(
            owner_id=owner.owner_id,
            name=f"Syn{'Cat' if species == 'cat' else 'Dog'} {name}",
            species=species,
            breed_id=breed.breed_id if rng.random() < 0.8 else None,
            weight_kg=weight if filled else None,
            size_band=size_band_from_weight(weight, species) if filled else None,
            size_source="weight" if filled else None,
            coat_type=rng.choice(COAT_TYPES_BY_SPECIES[species]) if filled else None,
            coat_thickness=rng.choice([1, 2, 2, 3]) if filled else None,
            handling_score=rng.randint(1, 5) if filled else None,
        )
        session.add(pet)
        session.flush()
        size_factor = {"s": 0.8, "m": 1.0, "l": 1.25, "xl": 1.5}.get(
            size_band_from_weight(weight, species) or "m", 1.0
        )
        base = (breed.base_groom_minutes or 75) * size_factor
        return _Dog(
            pet=pet,
            base=int(base),
            interval=rng.choice([21, 28, 35, 42, 49]),
            usual_condition=rng.choice([1, 2, 3, 3, 4, 4, 5]),
        )

    names = DOG_NAMES[:]
    rng.shuffle(names)
    two_dog_owners: list[tuple[_Dog, _Dog]] = []
    for i in range(27):
        owner = Owner(name=f"Syn Recent Owner {i + 1:02d}")
        session.add(owner)
        session.flush()
        first = make_animal(owner, names.pop(), "dog")
        dogs.append(first)
        if i < 3:  # three owners bring two dogs
            second = make_animal(owner, names.pop(), "dog")
            dogs.append(second)
            two_dog_owners.append((first, second))
    for cat_name in CAT_NAMES:
        owner = Owner(name=f"Syn Recent Owner {cat_name}")
        session.add(owner)
        session.flush()
        dogs.append(make_animal(owner, cat_name, "cat"))

    # --- schedule: first visit in the first half, then every `interval` days ---
    partner = {a.pet.pet_id: b for a, b in two_dog_owners} | {
        b.pet.pet_id: a for a, b in two_dog_owners
    }
    planned: list[tuple[date, _Dog]] = []
    seen: set[int] = set()
    for dog in dogs:
        if dog.pet.pet_id in seen:
            continue
        d = rng.choice(days[: len(days) // 2])
        while d <= today:
            day = min(days, key=lambda x: abs((x - d).days))  # nearest salon day
            planned.append((day, dog))
            if dog.pet.pet_id in partner:  # the second dog comes along
                planned.append((day, partner[dog.pet.pet_id]))
            d += timedelta(days=dog.interval + rng.randint(-5, 5))
        seen.add(dog.pet.pet_id)
        if dog.pet.pet_id in partner:
            seen.add(partner[dog.pet.pet_id].pet.pet_id)

    # --- visits, oldest first so "days since last" and estimates use the past ---
    added = 0
    for day, dog in sorted(planned, key=lambda x: (x[0], x[1].pet.pet_id)):
        condition = max(0, min(5, dog.usual_condition + rng.choice([-1, 0, 0, 1])))
        shaved = condition <= 1 and rng.random() < 0.7
        minutes = dog.base + (5 - condition) * 9 + (25 if shaved else 0)
        minutes = _round5(minutes * rng.uniform(0.85, 1.2))
        # Prices follow the list more than the work: bad coats are undercharged.
        price = _round5(30 + dog.base * 0.6 + (5 - condition) * 2 + rng.uniform(-5, 10))
        service = _service_for(dog.pet.species, dog.base, services)

        days_since, p50, p90 = compute_visit_predictions(session, pet=dog.pet, visit_date=day)
        visit = Visit(
            pet_id=dog.pet.pet_id,
            owner_id=dog.pet.owner_id,
            visit_date=day,
            status="completed",
            condition_score=condition,
            shaved_down=shaved,
            actual_minutes=minutes,
            booked_service_id=service.service_id,
            actual_service_id=service.service_id,
            days_since_last=days_since,
            predicted_min_p50=p50,
            predicted_min_p90=p90,
            final_price=price,
            tip=_round5(rng.uniform(2, 10)) if rng.random() < 0.3 else None,
        )
        session.add(visit)
        session.flush()
        for slug, chance in (("de_shed", 0.15), ("nail_grind", 0.15), ("hand_stripping", 0.06)):
            if slug in add_ons and rng.random() < chance:
                session.add(VisitAddOn(visit_id=visit.visit_id, add_on_id=add_ons[slug].add_on_id))
        added += 1

    session.flush()
    return added
