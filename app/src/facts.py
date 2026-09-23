"""Facts for a card, computed in code: the LLM words them, it never invents them."""

from dataclasses import dataclass

from src.models import Vendor
from src.schemas import Language, MatchedOn, RecommendIn, Role

ROLE_FACTS = {
    "best_match": "роль карточки: точнее всех попадает в заказ, больше всех совпавших условий",
    "best_price": "роль карточки: самая низкая цена среди свободных и подходящих",
    "premium": "роль карточки: самый дорогой вариант, который укладывается в бюджет",
}


@dataclass(frozen=True)
class Pick:
    vendor: Vendor
    role: Role
    matched_on: list[MatchedOn]
    closest_by_description: bool = False


def format_kzt(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " ₸"


def get_language_labels(values: list[str]) -> str:
    return ", ".join(Language(value).label for value in values)


def has_hours_reserve(vendor: Vendor, order: RecommendIn) -> bool:
    return vendor.max_hours is None or vendor.max_hours >= (order.duration_hours or 0) + 2


def get_alternative_gaps(pick: Pick, best: Pick, order: RecommendIn) -> list[str]:
    """Every scoring component where the best match beats this vendor: the list must be complete,
    otherwise "only" in the explanation is a lie."""
    vendor, leader = pick.vendor, best.vendor
    gaps = []
    if "description" in best.matched_on and "description" not in pick.matched_on:
        gaps.append("молчит о формате в описании")
    extra_languages = set(leader.languages) - set(vendor.languages)
    if extra_languages:
        spoken = " и ".join(Language(value).label for value in sorted(extra_languages))
        gaps.append(f"у первого ещё {spoken}")
    if has_hours_reserve(leader, order) and not has_hours_reserve(vendor, order):
        gaps.append("меньше запаса по часам")
    if vendor.synthetic and not leader.synthetic:
        gaps.append("профиль синтетический")
    if vendor.price_imputed and not leader.price_imputed:
        gaps.append("цена в каталоге оценочная")
    return gaps


def get_alternative_reason(pick: Pick, picks: list[Pick], order: RecommendIn) -> str:
    """The concrete gap to the best match: "one more option" makes the card interchangeable."""
    best = next((other for other in picks if other.role == "best_match"), None)
    if best is None:
        return "ещё один вариант, проходящий все условия"
    gaps = get_alternative_gaps(pick, best, order)
    if len(gaps) == 1:
        return f"проходит все условия, уступает первому только тем, что {gaps[0]}"
    if gaps:
        return "проходит все условия, уступает первому по мелочам: " + ", ".join(gaps)
    price_gap = pick.vendor.price_from_kzt - best.vendor.price_from_kzt
    if price_gap < 0:
        return f"проходит все условия и дешевле первого на {format_kzt(-price_gap)}"
    if price_gap > 0:
        return f"проходит все условия, дороже первого на {format_kzt(price_gap)}"
    return "проходит все условия, по данным каталога равен первому"


def get_role_fact(pick: Pick, picks: list[Pick], order: RecommendIn) -> str:
    if pick.role == "alternative":
        return "роль карточки: " + get_alternative_reason(pick, picks, order)
    return ROLE_FACTS[pick.role]


def get_distinctions(pick: Pick, picks: list[Pick]) -> list[str]:
    others = [other.vendor for other in picks if other.vendor.id != pick.vendor.id]
    if not others:
        return []
    vendor, distinctions = pick.vendor, []
    unique_languages = set(vendor.languages) - {lang for o in others for lang in o.languages}
    if unique_languages:
        spoken = " и ".join(Language(value).prepositional for value in sorted(unique_languages))
        distinctions.append(
            f"единственный из показанных работает на {spoken}, "
            "гости на этом языке не выпадут из программы"
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
        get_role_fact(pick, picks, order),
        f"цена по каталогу {format_kzt(vendor.price_from_kzt)}, "
        f"это {share}% бюджета {format_kzt(order.budget_kzt)}, остаётся {remainder} на остальное",
        f"свободен {order.event_date:%d.%m.%Y}",
        f"берёт формат «{order.event_format.label}»"
        + ("; в описании прямо упоминает этот формат" if "description" in pick.matched_on else ""),
        f"языки работы: {get_language_labels(vendor.languages)}"
        + (f"; заказчику нужны: {get_language_labels(order.languages)}" if order.languages else ""),
    ]
    if pick.closest_by_description:
        facts.append("из прошедших отбор его описание по смыслу ближе всех к запросу")
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
            f"из {pool} в этой категории в городе {city} на эту дату заняты {busy}, "
            "выбор на дату уже сужается, закрепить лучше пораньше"
            if busy
            else f"в городе {city} на эту дату в этой категории никто не занят, спешить не нужно"
        )
    if vendor.price_imputed:
        facts.append("цена в каталоге оценочная")
    return facts
