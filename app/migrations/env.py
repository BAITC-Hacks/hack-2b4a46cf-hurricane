"""Alembic async environment. URL comes from settings, metadata from src.models."""

import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config

from src import models  # noqa: F401  registers tables on Base.metadata
from src.config import settings
from src.db import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata


def run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = async_engine_from_config(config.get_section(config.config_ini_section, {}))
    async with engine.connect() as connection:
        await connection.run_sync(run_migrations)
    await engine.dispose()


asyncio.run(run_async_migrations())
