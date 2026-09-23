"""Applies migrations, then upserts data/vendors.csv into `vendors`. Safe to run on every deploy."""

import asyncio
import csv
from datetime import date
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from src.db import SessionFactory, engine
from src.models import Vendor
from src.schemas import Category, City, EventFormat, Language, Option

APP_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = APP_DIR / "data" / "vendors.csv"


def apply_migrations() -> None:
    # Railway runs a single pre-deploy command, so migrations and seed share one entry point.
    config = Config(str(APP_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(APP_DIR / "migrations"))
    command.upgrade(config, "head")


def split_list(raw: str) -> list[str]:
    return [part.strip() for part in raw.split("|") if part.strip()]


def get_option_values(raw: str, option: type[Option]) -> list[str]:
    values_by_label = {member.label: member.value for member in option}
    labels = split_list(raw)
    # A label missing from the vocabulary would silently vanish from filters, so the seed fails.
    unknown = [label for label in labels if label not in values_by_label]
    if unknown:
        raise ValueError(f"{option.__name__} has no value for {unknown}, add it to schemas.py")
    return [values_by_label[label] for label in labels]


def parse_vendor_row(row: dict[str, str]) -> dict:
    return {
        "id": row["id"],
        "name": row["anon_name"],
        "categories": get_option_values(row["categories"], Category),
        "city": get_option_values(row["city"], City)[0],
        "price_from_kzt": int(row["price_from_kzt"]),
        "event_formats": get_option_values(row["event_formats"], EventFormat),
        "languages": get_option_values(row["languages"], Language),
        "max_hours": int(row["max_hours"]) if row["max_hours"] else None,
        "busy_dates": [date.fromisoformat(day) for day in split_list(row["busy_dates"])],
        "description": row["description"].strip(),
        "synthetic": row["synthetic"] == "True",
        "city_imputed": row["city_imputed"] == "True",
        "price_imputed": row["price_imputed"] == "True",
    }


def read_vendor_rows() -> list[dict]:
    with DATASET_PATH.open(encoding="utf-8", newline="") as file:
        return [parse_vendor_row(row) for row in csv.DictReader(file)]


async def seed_vendors() -> int:
    rows = read_vendor_rows()
    statement = insert(Vendor).values(rows)
    # Upsert keeps the CSV as the source of truth: edited rows update, reruns do nothing new.
    statement = statement.on_conflict_do_update(
        index_elements=[Vendor.id],
        set_={column: statement.excluded[column] for column in rows[0] if column != "id"},
    )
    async with SessionFactory() as session:
        await session.execute(statement)
        await session.commit()
        return await session.scalar(select(func.count()).select_from(Vendor))


async def main() -> None:
    total = await seed_vendors()
    await engine.dispose()
    print(f"vendors in table: {total}")


if __name__ == "__main__":
    # Alembic's env.py starts its own event loop, so it must finish before ours begins.
    apply_migrations()
    asyncio.run(main())
