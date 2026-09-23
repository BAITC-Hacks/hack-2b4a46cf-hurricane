"""POST /recommend: pool, hard filters, scoring with description ranks, three role slots, hints."""

import asyncio
import re
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_session
from src.embeddings import fetch_query_embedding, get_description_ranks
from src.errors import UpstreamError
from src.explain import build_cards
from src.facts import Pick
from src.filters import get_rejection_reasons, get_rejections
from src.models import Vendor
from src.schemas import EventFormat, MatchedOn, RecommendIn, RecommendOut
from src.suggestions import (
    fetch_city_suggestions,
    get_budget_suggestion,
    get_date_suggestions,
    get_duration_suggestion,
)

router = APIRouter()

FORMAT_PATTERNS = {
    EventFormat.wedding: r"свад",
    EventFormat.toi: r"\bто(й|я|е|ю|ев|ях|ям)\b",
    EventFormat.corporate: r"корпорат",
    EventFormat.conference: r"конферен|форум",
    EventFormat.anniversary: r"юбиле",
    EventFormat.birthday: r"рожден",
}
# The three descriptions closest to the order by meaning get 3, 2 and 1 points.
DESCRIPTION_POINTS = {1: 3, 2: 2, 3: 1}
DB_TIMEOUT_SECONDS = 5


def is_format_in_description(vendor: Vendor, event_format: str) -> bool:
    return re.search(FORMAT_PATTERNS[event_format], vendor.description, re.IGNORECASE) is not None


def get_match_score(vendor: Vendor, order: RecommendIn, description_rank: int | None) -> int:
    score = 3 if is_format_in_description(vendor, order.event_format) else 0
    score += DESCRIPTION_POINTS.get(description_rank, 0)
    score += len(set(vendor.languages) - set(order.languages))
    has_hours_reserve = (
        vendor.max_hours is None or vendor.max_hours >= (order.duration_hours or 0) + 2
    )
    score += int(has_hours_reserve)
    score += 2 * int(not vendor.synthetic) + int(not vendor.price_imputed)
    score += int(vendor.price_from_kzt <= order.budget_kzt * 0.8)
    return score


def get_matched_on(vendor: Vendor, order: RecommendIn, is_closest: bool) -> list[MatchedOn]:
    matched: list[MatchedOn] = ["date", "format", "budget"]
    if order.duration_hours and vendor.max_hours is not None:
        matched.append("duration")
    if order.languages:
        matched.append("language")
    if is_closest or is_format_in_description(vendor, order.event_format):
        matched.append("description")
    return matched


def pick_role_vendors(passed: list[Vendor], order: RecommendIn, ranks: dict) -> list[Pick]:
    if not passed:
        return []
    by_score = sorted(
        passed, key=lambda v: (-get_match_score(v, order, ranks.get(v.id)), v.price_from_kzt, v.id)
    )
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
    picks = []
    for vendor_id, role in list(picked.items())[:3]:
        vendor, is_closest = vendors_by_id[vendor_id], ranks.get(vendor_id) == 1
        picks.append(Pick(vendor, role, get_matched_on(vendor, order, is_closest), is_closest))
    return picks


async def fetch_pool(session: AsyncSession, order: RecommendIn) -> list[Vendor]:
    statement = select(Vendor).where(
        Vendor.city == order.city, Vendor.categories.any(order.category)
    )
    try:
        async with asyncio.timeout(DB_TIMEOUT_SECONDS):
            return list(await session.scalars(statement))
    except TimeoutError as error:
        raise UpstreamError("Каталог не отвечает, повторите запрос") from error


@router.post("/recommend", response_model=RecommendOut)
async def recommend(
    order: RecommendIn, session: Annotated[AsyncSession, Depends(get_session)]
) -> RecommendOut:
    pool, query_embedding = await asyncio.gather(
        fetch_pool(session, order), fetch_query_embedding(order)
    )
    if not pool:
        return RecommendOut(
            outcome="no_category_in_city",
            cards=[],
            pool_size=0,
            passed_count=0,
            rejections=[],
            suggestions=await fetch_city_suggestions(session, order),
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
    picks = pick_role_vendors(passed, order, get_description_ranks(passed, query_embedding))
    cards = await build_cards(picks, order, busy_count, len(pool))
    return RecommendOut(
        outcome="matched" if cards else "no_candidates_pass",
        cards=cards,
        pool_size=len(pool),
        passed_count=len(passed),
        rejections=get_rejections(pool, order),
        suggestions=suggestions,
    )
