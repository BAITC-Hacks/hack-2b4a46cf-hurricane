"""Database tables. Schema changes go through Alembic: `uv run alembic revision --autogenerate`."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


class Vendor(Base):
    """A profile from data/vendors.csv. Lists stay as arrays: 66 rows need no joins."""

    __tablename__ = "vendors"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    categories: Mapped[list[str]] = mapped_column(ARRAY(String(64)))
    city: Mapped[str] = mapped_column(String(64))
    price_from_kzt: Mapped[int]
    event_formats: Mapped[list[str]] = mapped_column(ARRAY(String(32)))
    languages: Mapped[list[str]] = mapped_column(ARRAY(String(32)))
    # NULL means the work is not tied to hours on site: florist, decorator, souvenirs.
    max_hours: Mapped[int | None]
    busy_dates: Mapped[list[date]] = mapped_column(ARRAY(Date))
    description: Mapped[str] = mapped_column(Text)
    synthetic: Mapped[bool]
    city_imputed: Mapped[bool]
    price_imputed: Mapped[bool]
    # Filled by the seed when an OpenAI key is present; NULL keeps ranking on the format regex.
    description_embedding: Mapped[list[float] | None] = mapped_column(ARRAY(Float), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
