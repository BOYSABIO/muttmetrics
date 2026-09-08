"""Pydantic request/response models for the HTTP API."""

from muttmetrics.api.schemas.dogs import DogResponse, UpsertDogRequest
from muttmetrics.api.schemas.owners import OwnerResponse, UpsertOwnerRequest
from muttmetrics.api.schemas.visits import CreateVisitRequest, VisitResponse

__all__ = [
    "CreateVisitRequest",
    "DogResponse",
    "OwnerResponse",
    "UpsertDogRequest",
    "UpsertOwnerRequest",
    "VisitResponse",
]
