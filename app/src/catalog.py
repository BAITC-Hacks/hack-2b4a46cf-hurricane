"""GET /catalog/options and GET /vendors: filter vocabularies and the whole catalog for the list."""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_session
from src.errors import UpstreamError
from src.models import Vendor
from src.schemas import (
    CATALOG_DATE_FROM,
    CATALOG_DATE_TO,
    CatalogOptionsOut,
    Category,
    City,
    EventFormat,
    Language,
    VendorOut,
    get_option,
    get_options,
)

router = APIRouter()

DB_TIMEOUT_SECONDS = 5


@router.get("/catalog/options", response_model=CatalogOptionsOut)
async def get_catalog_options() -> CatalogOptionsOut:
    return CatalogOptionsOut(
        cities=[get_option(member) for member in City],
        categories=[get_option(member) for member in Category],
        event_formats=[get_option(member) for member in EventFormat],
        languages=[get_option(member) for member in Language],
        date_from=CATALOG_DATE_FROM,
        date_to=CATALOG_DATE_TO,
    )


def get_vendor_out(vendor: Vendor) -> VendorOut:
    return VendorOut(
        id=vendor.id,
        name=vendor.name,
        categories=get_options(vendor.categories, Category),
        city=get_option(City(vendor.city)),
        price_from_kzt=vendor.price_from_kzt,
        event_formats=get_options(vendor.event_formats, EventFormat),
        languages=get_options(vendor.languages, Language),
        max_hours=vendor.max_hours,
        description=vendor.description,
        synthetic=vendor.synthetic,
        price_imputed=vendor.price_imputed,
        city_imputed=vendor.city_imputed,
    )


@router.get("/vendors", response_model=list[VendorOut])
async def get_vendors(session: Annotated[AsyncSession, Depends(get_session)]) -> list[VendorOut]:
    try:
        async with asyncio.timeout(DB_TIMEOUT_SECONDS):
            vendors = await session.scalars(select(Vendor).order_by(Vendor.id))
    except TimeoutError as error:
        raise UpstreamError("Каталог не отвечает, повторите запрос") from error
    return [get_vendor_out(vendor) for vendor in vendors]
