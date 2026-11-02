"""Pydantic request/response models for the HTTP API."""

from muttmetrics.api.schemas.owners import OwnerResponse, UpsertOwnerRequest
from muttmetrics.api.schemas.pets import PetResponse, UpsertPetRequest
from muttmetrics.api.schemas.photos import PhotoResponse
from muttmetrics.api.schemas.visits import CreateVisitRequest, VisitResponse

__all__ = [
    "CreateVisitRequest",
    "OwnerResponse",
    "PetResponse",
    "UpsertOwnerRequest",
    "UpsertPetRequest",
    "VisitResponse",
    "PhotoResponse",
]
