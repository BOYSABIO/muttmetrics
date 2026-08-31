"""ORM models - import all tables so metadata is complete for Alembic."""

from muttmetrics.models.breed import Breed
from muttmetrics.models.dog import Dog
from muttmetrics.models.owner import Owner
from muttmetrics.models.service import Service
from muttmetrics.models.visit import Visit

__all__ = ["Breed", "Dog", "Owner", "Service", "Visit"]
