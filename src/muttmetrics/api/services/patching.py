"""Shared rules for partial (PATCH) updates."""

from typing import Any

from muttmetrics.db.base import Base


def reject_null_for_required_columns(model: type[Base], updates: dict[str, Any]) -> None:
    """Raise ValueError if the client explicitly sent null for a NOT NULL column.

    ``model_dump(exclude_unset=True)`` keeps keys the client actually sent, so
    ``{"locale": null}`` arrives here as ``updates["locale"] is None``. Without
    this check it reaches Postgres and fails as an IntegrityError (500). The
    table metadata already knows which columns are NOT NULL, so new required
    columns are covered without touching this function.
    """
    columns = model.__table__.columns
    for key, value in updates.items():
        if value is None and key in columns and not columns[key].nullable:
            raise ValueError(f"{key} cannot be null")
