"""Service reference table - groom types and baseline minutes/price."""

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from muttmetrics.db.base import Base


class Service(Base):
    """
    Bookable service types (bath, full groom, nails, etc.).

    'slug' is the stable programmatic key (e.g. for API and seed data).
    """

    __tablename__ = "service"

    service_id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    name_de: Mapped[str | None] = mapped_column(String, nullable=True)
    name_en: Mapped[str | None] = mapped_column(String, nullable=True)
    base_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    buffer_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_base: Mapped[float | None] = mapped_column(Numeric, nullable=True)
