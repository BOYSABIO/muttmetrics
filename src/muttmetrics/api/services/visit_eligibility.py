"""Shared 'counts as a visit' rule (#171 / glossary #126)."""

from __future__ import annotations

from sqlalchemy import ColumnElement, or_

from muttmetrics.models import Visit


def visit_counts_clause() -> ColumnElement[bool]:
    """True for visits that count toward history (completed or legacy NULL).

    Excludes cancelled and no_show. Same rule as analytics.md / metrics.
    """
    return or_(Visit.status.is_(None), Visit.status == "completed")
