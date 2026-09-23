"""Database tables. Schema changes go through Alembic: `uv run alembic revision --autogenerate`."""

from src.db import Base  # noqa: F401  new tables subclass Base here so Alembic sees them
