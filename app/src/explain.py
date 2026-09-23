"""Card explanations: facts are computed in code, the LLM only words them, a template is the net."""

import json
import logging
import re
from pathlib import Path

from src.errors import UpstreamError
from src.facts import (
    Pick,
    format_kzt,
    get_alternative_reason,
    get_distinctions,
    get_language_labels,
    get_pick_facts,
)
from src.llm import fetch_llm_json
from src.models import Vendor
from src.schemas import (
    Category,
    City,
    Language,
    RecommendIn,
    VendorCardOut,
    get_option,
    get_options,
)

logger = logging.getLogger(__name__)

BANNED_PHRASES = (
    "отличный выбор",
    "идеальн",
    "для вашего мероприятия",
    "профессионал своего",
    "надёжн",
    "качественн",
    "больше всего совпадений",
    "карточк",
    "подборк",
)
MAX_SENTENCES = 2
SENTENCE_END = re.compile(r"[.!?]+(?=\s|$)")
# A Latin letter inside a Cyrillic word ("датe") is a model typo the reader will notice.
MIXED_SCRIPT_WORD = re.compile(r"\b(?=\w*[а-яё])(?=\w*[a-z])\w+\b", re.IGNORECASE)
SYSTEM_PROMPT = (Path(__file__).parent / "explain_prompt.md").read_text(encoding="utf-8")


def get_order_labels(order: RecommendIn) -> dict:
    # The LLM words facts in Russian, so it sees labels, not the latin values from the URL.
    return {
        **order.model_dump(mode="json"),
        "city": order.city.label,
        "event_format": order.event_format.label,
        "category": order.category.label,
        "languages": [language.label for language in order.languages],
    }


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
        "alternative": f"{get_alternative_reason(pick, picks).capitalize()}: от {price}, "
        f"остаётся {remainder} на остальное.",
    }[pick.role]
    note = " Цена ориентировочная, уточняйте." if vendor.price_imputed else ""
    return f"{lead} {get_template_second_sentence(pick, picks, order, busy, pool)}{note}"


def is_valid_explanation(text: object, vendor: Vendor) -> bool:
    if not isinstance(text, str) or not 20 <= len(text) <= 320:
        return False
    if len(SENTENCE_END.findall(text)) > MAX_SENTENCES or MIXED_SCRIPT_WORD.search(text):
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
