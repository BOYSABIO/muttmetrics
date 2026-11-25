"""Monthly fixed costs (#229, #59): one row per change, "from this month on".

Only rent for now (utilities included). The amounts are the salon's own
figures, so they are set on the box with ``ops/rent.py`` and never committed.
The dashboard reads them through ``metric_rent()`` (ADR-003), not this model.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from muttmetrics.db.base import Base

FIXED_COST_KINDS = ("rent",)


class FixedCost(Base):
    __tablename__ = "fixed_cost"
    __table_args__ = (
        CheckConstraint("kind IN ('rent')", name="ck_fixed_cost_kind"),
        CheckConstraint("monthly_amount >= 0", name="ck_fixed_cost_amount"),
        CheckConstraint("EXTRACT(DAY FROM valid_from) = 1", name="ck_fixed_cost_first_of_month"),
        UniqueConstraint("kind", "valid_from", name="uq_fixed_cost_kind_valid_from"),
    )

    fixed_cost_id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    monthly_amount: Mapped[float] = mapped_column(Numeric, nullable=False)
    # First day of the month the amount applies from; until the next row.
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
