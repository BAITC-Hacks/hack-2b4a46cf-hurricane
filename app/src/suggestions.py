"""Relaxed queries that would return more vendors: nearby dates, budget, hours, other cities."""

from collections import Counter
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.filters import get_rejection_reasons
from src.models import Vendor
from src.schemas import CATALOG_DATE_FROM, CATALOG_DATE_TO, RecommendIn, SuggestionOut

DATE_OFFSETS = (-1, 1, -2, 2, -3, 3)


def get_date_suggestions(pool: list[Vendor], order: RecommendIn, passed_count: int) -> list:
    suggestions = []
    for offset in DATE_OFFSETS:
        day = order.event_date + timedelta(days=offset)
        if not CATALOG_DATE_FROM <= day <= CATALOG_DATE_TO:
            continue
        relaxed = order.model_copy(update={"event_date": day})
        count = sum(1 for vendor in pool if not get_rejection_reasons(vendor, relaxed))
        if count > passed_count:
            suggestions.append(SuggestionOut(kind="date", count=count, event_date=day))
        if len(suggestions) == 2:
            break
    return suggestions


def get_budget_suggestion(pool: list[Vendor], order: RecommendIn, passed_count: int) -> list:
    prices = sorted(
        vendor.price_from_kzt
        for vendor in pool
        if get_rejection_reasons(vendor, order) == ["budget"]
    )
    if not prices:
        return []
    added = min(3 - passed_count, len(prices))
    return [SuggestionOut(kind="budget", count=passed_count + added, budget_kzt=prices[added - 1])]


def get_duration_suggestion(pool: list[Vendor], order: RecommendIn, passed_count: int) -> list:
    hours = sorted(
        (
            vendor.max_hours
            for vendor in pool
            if get_rejection_reasons(vendor, order) == ["duration"]
        ),
        reverse=True,
    )
    if not hours:
        return []
    added = min(3 - passed_count, len(hours))
    return [
        SuggestionOut(kind="duration", count=passed_count + added, duration_hours=hours[added - 1])
    ]


def get_city_suggestions(other_cities_pool: list[Vendor], order: RecommendIn) -> list:
    # Counts vendors that pass every condition, not just exist: "в Астане подходят 2" is actionable.
    passing = Counter(
        vendor.city for vendor in other_cities_pool if not get_rejection_reasons(vendor, order)
    )
    return [
        SuggestionOut(kind="city", count=count, city=city)
        for city, count in sorted(passing.items(), key=lambda pair: (-pair[1], pair[0]))
    ]


async def fetch_city_suggestions(session: AsyncSession, order: RecommendIn) -> list:
    statement = select(Vendor).where(
        Vendor.categories.any(order.category), Vendor.city != order.city
    )
    return get_city_suggestions(list(await session.scalars(statement)), order)
