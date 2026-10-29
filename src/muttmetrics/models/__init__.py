"""ORM models - import all tables so metadata is complete for Alembic."""

from muttmetrics.models.add_on import AddOn
from muttmetrics.models.breed import Breed
from muttmetrics.models.dog import Dog
from muttmetrics.models.owner import Owner
from muttmetrics.models.photo import Photo
from muttmetrics.models.service import Service
from muttmetrics.models.visit import Visit
from muttmetrics.models.visit_add_on import VisitAddOn

__all__ = [
    "AddOn",
    "Breed",
    "Dog",
    "Owner",
    "Photo",
    "Service",
    "Visit",
    "VisitAddOn",
]
