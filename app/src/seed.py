"""Loads data/vendors.csv into `vendors`. Idempotent, so it runs on every deploy."""

import asyncio
import csv
from datetime import date
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from src.db import SessionFactory, engine
from src.models import Vendor

DATASET_PATH = Path(__file__).resolve().parent.parent / "data" / "vendors.csv"


def split_list(raw: str) -> list[str]:
    return [part.strip() for part in raw.split("|") if part.strip()]


def parse_vendor_row(row: dict[str, str]) -> dict:
    return {
        "id": row["id"],
        "name": row["anon_name"],
        "categories": split_list(row["categories"]),
        "city": row["city"],
        "price_from_kzt": int(row["price_from_kzt"]),
        "event_formats": split_list(row["event_formats"]),
        "languages": split_list(row["languages"]),
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
    asyncio.run(main())
