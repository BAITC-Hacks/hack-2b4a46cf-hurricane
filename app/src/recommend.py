"""POST /recommend: hard filters with rejection reasons, three role slots, relaxed-query hints."""

import asyncio
import re
from collections import Counter
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_session
from src.errors import UpstreamError
from src.explain import Pick, build_cards
from src.models import Vendor
from src.schemas import (
    CATALOG_DATE_FROM,
    CATALOG_DATE_TO,
    EventFormat,
    MatchedOn,
    RecommendIn,
    RecommendOut,
    RejectionOut,
    SuggestionOut,
)

router = APIRouter()

# Order matters: a vendor is counted under its first failed check, so counts sum to the pool.
REASON_ORDER = ("busy", "format", "budget", "duration", "language")
FORMAT_PATTERNS = {
    EventFormat.wedding: r"свад",
    EventFormat.toi: r"\bто(й|я|е|ю|ев|ях|ям)\b",
    EventFormat.corporate: r"корпорат",
    EventFormat.conference: r"конферен|форум",
    EventFormat.anniversary: r"юбиле",
    EventFormat.birthday: r"рожден",
}
DATE_OFFSETS = (-1, 1, -2, 2, -3, 3)
DB_TIMEOUT_SECONDS = 5


def get_rejection_reasons(vendor: Vendor, order: RecommendIn) -> list[str]:
    checks = {
        "busy": order.event_date in vendor.busy_dates,
        "format": order.event_format not in vendor.event_formats,
        "budget": vendor.price_from_kzt > order.budget_kzt,
        "duration": bool(order.duration_hours)
        and vendor.max_hours is not None
        and vendor.max_hours < order.duration_hours,
        "language": not set(order.languages) <= set(vendor.languages),
    }
    return [reason for reason in REASON_ORDER if checks[reason]]


def is_format_in_description(vendor: Vendor, event_format: str) -> bool:
    return re.search(FORMAT_PATTERNS[event_format], vendor.description, re.IGNORECASE) is not None


def get_match_score(vendor: Vendor, order: RecommendIn) -> int:
    score = 3 if is_format_in_description(vendor, order.event_format) else 0
    score += len(set(vendor.languages) - set(order.languages))
    has_hours_reserve = (
        vendor.max_hours is None or vendor.max_hours >= (order.duration_hours or 0) + 2
    )
    score += int(has_hours_reserve)
    score += 2 * int(not vendor.synthetic) + int(not vendor.price_imputed)
    score += int(vendor.price_from_kzt <= order.budget_kzt * 0.8)
    return score


def get_matched_on(vendor: Vendor, order: RecommendIn) -> list[MatchedOn]:
    matched: list[MatchedOn] = ["date", "format", "budget"]
    if order.duration_hours and vendor.max_hours is not None:
        matched.append("duration")
    if order.languages:
        matched.append("language")
    if is_format_in_description(vendor, order.event_format):
        matched.append("description")
    return matched


def pick_role_vendors(passed: list[Vendor], order: RecommendIn) -> list[Pick]:
    if not passed:
        return []
    by_score = sorted(passed, key=lambda v: (-get_match_score(v, order), v.price_from_kzt, v.id))
    role_winners = {
        "best_match": by_score[0],
        "best_price": min(passed, key=lambda v: (v.price_from_kzt, v.id)),
        "premium": min(passed, key=lambda v: (-v.price_from_kzt, v.id)),
    }
    picked: dict[str, str] = {}
    for role, vendor in role_winners.items():
        picked.setdefault(vendor.id, role)
    # A vendor winning two roles frees a slot: it goes to the next best by score.
    for vendor in by_score:
        if len(picked) >= 3:
            break
        picked.setdefault(vendor.id, "alternative")
    vendors_by_id = {vendor.id: vendor for vendor in passed}
    return [
        Pick(vendors_by_id[vendor_id], role, get_matched_on(vendors_by_id[vendor_id], order))
        for vendor_id, role in list(picked.items())[:3]
    ]


def get_rejections(pool: list[Vendor], order: RecommendIn) -> list[RejectionOut]:
    first_reasons = Counter(
        reasons[0] for vendor in pool if (reasons := get_rejection_reasons(vendor, order))
    )
    return [
        RejectionOut(reason=r, count=first_reasons[r]) for r in REASON_ORDER if first_reasons[r]
    ]


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


async def fetch_pool(session: AsyncSession, order: RecommendIn) -> list[Vendor]:
    statement = select(Vendor).where(
        Vendor.city == order.city, Vendor.categories.any(order.category)
    )
    try:
        async with asyncio.timeout(DB_TIMEOUT_SECONDS):
            return list(await session.scalars(statement))
    except TimeoutError as error:
        raise UpstreamError("Каталог не отвечает, повторите запрос") from error


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


@router.post("/recommend", response_model=RecommendOut)
async def recommend(
    order: RecommendIn, session: Annotated[AsyncSession, Depends(get_session)]
) -> RecommendOut:
    pool = await fetch_pool(session, order)
    if not pool:
        suggestions = await fetch_city_suggestions(session, order)
        return RecommendOut(
            outcome="no_category_in_city",
            cards=[],
            pool_size=0,
            passed_count=0,
            rejections=[],
            suggestions=suggestions,
        )
    passed = [vendor for vendor in pool if not get_rejection_reasons(vendor, order)]
    suggestions = []
    if len(passed) < 3:
        suggestions = get_date_suggestions(pool, order, len(passed))
        suggestions += get_budget_suggestion(pool, order, len(passed))
        suggestions += get_duration_suggestion(pool, order, len(passed))
    if not passed:
        suggestions += await fetch_city_suggestions(session, order)
    busy_count = sum(1 for vendor in pool if order.event_date in vendor.busy_dates)
    cards = await build_cards(pick_role_vendors(passed, order), order, busy_count, len(pool))
    return RecommendOut(
        outcome="matched" if cards else "no_candidates_pass",
        cards=cards,
        pool_size=len(pool),
        passed_count=len(passed),
        rejections=get_rejections(pool, order),
        suggestions=suggestions,
    )
