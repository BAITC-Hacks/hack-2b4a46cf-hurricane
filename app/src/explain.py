"""Card explanations: facts are computed in code, the LLM only words them, a template is the net."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from src.errors import UpstreamError
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

ROLE_FACTS = {
    "best_match": "роль карточки: больше всего совпадений с заказом",
    "best_price": "роль карточки: самая низкая цена среди свободных и подходящих",
    "premium": "роль карточки: самый дорогой вариант, который укладывается в бюджет",
    "alternative": "роль карточки: ещё один вариант, проходящий все условия",
}
BANNED_PHRASES = ("отличный выбор", "идеальн", "для вашего мероприятия", "профессионал своего")
SYSTEM_PROMPT = (Path(__file__).parent / "explain_prompt.md").read_text(encoding="utf-8")


@dataclass(frozen=True)
class Pick:
    vendor: Vendor
    role: Role
    matched_on: list[MatchedOn]


def format_kzt(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " ₸"


def get_language_labels(values: list[str]) -> str:
    return ", ".join(Language(value).label for value in values)


def get_order_labels(order: RecommendIn) -> dict:
    # The LLM words facts in Russian, so it sees labels, not the latin values from the URL.
    return {
        **order.model_dump(mode="json"),
        "city": order.city.label,
        "event_format": order.event_format.label,
        "category": order.category.label,
        "languages": [language.label for language in order.languages],
    }


def get_distinctions(pick: Pick, picks: list[Pick]) -> list[str]:
    others = [other.vendor for other in picks if other.vendor.id != pick.vendor.id]
    if not others:
        return []
    vendor, distinctions = pick.vendor, []
    unique_languages = set(vendor.languages) - {lang for o in others for lang in o.languages}
    if unique_languages:
        distinctions.append(
            "единственный из показанных работает на языках: "
            + get_language_labels(sorted(unique_languages))
            + ", гости на этом языке не выпадут из программы"
        )
    other_hours = [o.max_hours for o in others if o.max_hours is not None]
    if vendor.max_hours is not None and other_hours and vendor.max_hours > max(other_hours):
        distinctions.append(
            f"больше всех из показанных часов на площадке: до {vendor.max_hours} ч, "
            "хватит даже если программа затянется"
        )
    return distinctions


def get_pick_facts(
    pick: Pick, picks: list[Pick], order: RecommendIn, busy: int, pool: int
) -> list[str]:
    vendor = pick.vendor
    share = round(vendor.price_from_kzt * 100 / order.budget_kzt)
    remainder = format_kzt(order.budget_kzt - vendor.price_from_kzt)
    facts = [
        ROLE_FACTS[pick.role],
        f"цена от {format_kzt(vendor.price_from_kzt)}, "
        f"это {share}% бюджета {format_kzt(order.budget_kzt)}, остаётся {remainder} на остальное",
        f"свободен {order.event_date:%d.%m.%Y}",
        f"берёт формат «{order.event_format.label}»"
        + ("; в описании прямо упоминает этот формат" if "description" in pick.matched_on else ""),
        f"языки работы: {get_language_labels(vendor.languages)}"
        + (f"; заказчику нужны: {get_language_labels(order.languages)}" if order.languages else ""),
    ]
    if vendor.max_hours is None:
        facts.append("работа не привязана к часам на площадке")
    else:
        asked = f" при заказе на {order.duration_hours} ч" if order.duration_hours else ""
        facts.append(f"до {vendor.max_hours} ч на площадке{asked}")
    facts += get_distinctions(pick, picks)
    # Said once, on the first card: repeated on all three it makes the cards interchangeable.
    if pick is picks[0]:
        city = order.city.label
        facts.append(
            f"из {pool} в этой категории в городе {city} на эту дату заняты {busy}"
            if busy
            else f"в городе {city} на эту дату в этой категории никто не занят, спешить не нужно"
        )
    if vendor.price_imputed:
        facts.append("цена в каталоге оценочная")
    return facts


def get_template_second_sentence(
    pick: Pick, picks: list[Pick], order: RecommendIn, busy: int, pool: int
) -> str:
    vendor = pick.vendor
    day = f"{order.event_date:%d.%m}"
    if pick is picks[0]:
        if not busy:
            return f"Свободен {day}, как и вся категория на эту дату: можно выбирать спокойно."
        return (
            f"Свободен {day}, а {busy} из {pool} в категории уже заняты: с датой лучше не тянуть."
        )
    distinctions = get_distinctions(pick, picks)
    if distinctions:
        return distinctions[0][0].upper() + distinctions[0][1:] + "."
    if vendor.max_hours is None:
        return "Работа не привязана к часам на площадке: переработку считать не придётся."
    if order.duration_hours:
        return (
            f"Готов работать до {vendor.max_hours} ч, "
            f"заказ на {order.duration_hours} ч укладывается."
        )
    return f"Готов работать до {vendor.max_hours} ч, хватит и на затянувшуюся программу."


def get_template_explanation(
    pick: Pick, picks: list[Pick], order: RecommendIn, busy: int, pool: int
) -> str:
    vendor = pick.vendor
    price, budget = format_kzt(vendor.price_from_kzt), format_kzt(order.budget_kzt)
    remainder = format_kzt(order.budget_kzt - vendor.price_from_kzt)
    matches = [f"берёт формат «{order.event_format.label}»"]
    if "description" in pick.matched_on:
        matches.append("сам пишет о нём в описании")
    if order.languages:
        matches.append(f"работает на нужных языках: {get_language_labels(order.languages)}")
    lead = {
        "best_price": f"Самый бережный к бюджету: от {price}, остаётся {remainder} на остальное.",
        "premium": f"Если хочется размаха: самый дорогой из тех, кто укладывается в {budget}, "
        f"от {price}, запас всего {remainder}.",
        "best_match": f"Точнее всех попадает в заказ: {', '.join(matches)}. "
        f"От {price}, остаётся {remainder} на остальное.",
        "alternative": f"Запасной вариант, если первые не ответят: от {price}, "
        f"остаётся {remainder} на остальное.",
    }[pick.role]
    note = " Цена ориентировочная, уточняйте." if vendor.price_imputed else ""
    return f"{lead} {get_template_second_sentence(pick, picks, order, busy, pool)}{note}"


def is_valid_explanation(text: object, vendor: Vendor) -> bool:
    if not isinstance(text, str) or not 20 <= len(text) <= 400:
        return False
    lower = text.lower()
    # The LLM likes to add "estimated price" on its own: a fact absent from the catalog is a lie.
    if not vendor.price_imputed and ("ориентиров" in lower or "оценочн" in lower):
        return False
    return not any(phrase in lower for phrase in BANNED_PHRASES)


async def fetch_llm_explanations(
    picks: list[Pick], facts: dict[str, list[str]], order: RecommendIn
) -> dict:
    request = {
        "заказ": get_order_labels(order),
        "карточки": [
            {"id": p.vendor.id, "факты": facts[p.vendor.id], "описание": p.vendor.description[:700]}
            for p in picks
        ],
    }
    try:
        answer = await fetch_llm_json(SYSTEM_PROMPT, json.dumps(request, ensure_ascii=False))
    except UpstreamError as error:
        logger.warning("explanations fall back to template: %s", error)
        return {}
    explanations = answer.get("explanations")
    return explanations if isinstance(explanations, dict) else {}


async def build_cards(
    picks: list[Pick], order: RecommendIn, busy: int, pool: int
) -> list[VendorCardOut]:
    if not picks:
        return []
    facts = {p.vendor.id: get_pick_facts(p, picks, order, busy, pool) for p in picks}
    llm_texts = await fetch_llm_explanations(picks, facts, order)
    cards = []
    for pick in picks:
        text = llm_texts.get(pick.vendor.id)
        vendor = pick.vendor
        is_llm = is_valid_explanation(text, vendor)
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
                explanation=text.strip()
                if is_llm
                else get_template_explanation(pick, picks, order, busy, pool),
                explanation_source="llm" if is_llm else "template",
                synthetic=vendor.synthetic,
                price_imputed=vendor.price_imputed,
                city_imputed=vendor.city_imputed,
            )
        )
    return cards
