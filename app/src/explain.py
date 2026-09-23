"""Build recommendation explanations from verified vendor facts."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from src.errors import UpstreamError
from src.facts import Fact, get_vendor_facts
from src.llm import fetch_llm_json
from src.models import Vendor
from src.schemas import (
    Category,
    City,
    Language,
    MatchedOn,
    RecommendIn,
    Role,
    VendorCardOut,
    get_option,
    get_options,
)

logger = logging.getLogger(__name__)
SYSTEM_PROMPT = (Path(__file__).parent / "explain_prompt.md").read_text(encoding="utf-8")


@dataclass(frozen=True)
class Pick:
    vendor: Vendor
    role: Role
    matched_on: list[MatchedOn]


def format_kzt(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " ₸"


def get_verified_explanation(pick: Pick, order: RecommendIn, fact: Fact) -> str:
    vendor = pick.vendor
    price = f"цена от {format_kzt(vendor.price_from_kzt)}"
    if vendor.price_imputed:
        price += " (оценочная)"
    conditions = [f"формат «{order.event_format.label}»"]
    if order.languages:
        languages = ", ".join(language.label for language in order.languages)
        conditions.append(f"языки: {languages}")
    if order.duration_hours:
        if vendor.max_hours:
            conditions.append(
                f"запрошенные {order.duration_hours} ч входят в предел до {vendor.max_hours} ч"
            )
        else:
            conditions.append("предел часов в каталоге не указан")
    return (
        f"Свободен {order.event_date:%d.%m.%Y}; {price}; "
        f"подходит по условиям: {', '.join(conditions)}. {fact.text}"
    )


async def fetch_llm_fact_ids(
    picks: list[Pick], facts: dict[str, list[Fact]], order: RecommendIn
) -> dict[str, str]:
    request = {
        "order": {
            "category": order.category.label,
            "event_format": order.event_format.label,
            "languages": [language.label for language in order.languages],
            "duration_hours": order.duration_hours,
        },
        "vendors": [
            {
                "id": pick.vendor.id,
                "facts": [{"id": fact.id, "text": fact.text} for fact in facts[pick.vendor.id]],
            }
            for pick in picks
        ],
    }
    try:
        answer = await fetch_llm_json(SYSTEM_PROMPT, json.dumps(request, ensure_ascii=False))
    except (UpstreamError, TypeError, ValueError) as error:
        logger.warning("explanations fall back to verified facts: %s", error)
        return {}
    selections = answer.get("selected_facts") if isinstance(answer, dict) else None
    return selections if isinstance(selections, dict) else {}


async def build_cards(picks: list[Pick], order: RecommendIn) -> list[VendorCardOut]:
    if not picks:
        return []
    shown = [pick.vendor for pick in picks]
    facts = {pick.vendor.id: get_vendor_facts(pick.vendor, shown) for pick in picks}
    selected_ids = await fetch_llm_fact_ids(picks, facts, order)
    cards = []
    for pick in picks:
        vendor = pick.vendor
        selected = next(
            (fact for fact in facts[vendor.id] if fact.id == selected_ids.get(vendor.id)), None
        )
        fact = selected or facts[vendor.id][0]
        cards.append(
            VendorCardOut(
                id=vendor.id,
                name=vendor.name,
                categories=get_options(vendor.categories, Category),
                city=get_option(City(vendor.city)),
                price_from_kzt=vendor.price_from_kzt,
                languages=get_options(vendor.languages, Language),
                max_hours=vendor.max_hours,
                role=pick.role,
                matched_on=pick.matched_on,
                explanation=get_verified_explanation(pick, order, fact),
                explanation_source="llm" if selected else "template",
                synthetic=vendor.synthetic,
                price_imputed=vendor.price_imputed,
                city_imputed=vendor.city_imputed,
            )
        )
    return cards
