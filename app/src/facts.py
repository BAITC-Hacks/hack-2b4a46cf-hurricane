"""Extract conservative, source-backed distinctions for recommendation cards."""

from dataclasses import dataclass

from src.models import Vendor


@dataclass(frozen=True)
class Fact:
    id: str
    text: str


# Each phrase is used only when its source wording occurs in the vendor description.
DESCRIPTION_FACTS = (
    ("авторском цветочном оформлении", "В описании указано авторское цветочное оформление."),
    ("под цветовую палитру", "В описании указаны композиции под цветовую палитру мероприятия."),
    (
        "сезонными и привозными цветами",
        "В описании указана работа с сезонными и привозными цветами.",
    ),
    ("подвесные композиции", "В описании указаны подвесные цветочные композиции."),
    ("перед главой государства", "В описании указано выступление перед главой государства."),
    ("казахскую песню", "В описании указана казахская песня."),
    ("команда джигитов", "В описании коллектив назван командой джигитов."),
)


def get_vendor_facts(vendor: Vendor, shown: list[Vendor]) -> list[Fact]:
    others = [other for other in shown if other.id != vendor.id]
    facts = [
        Fact(f"description:{phrase}", wording)
        for phrase, wording in DESCRIPTION_FACTS
        if phrase in vendor.description.casefold()
        and not any(phrase in other.description.casefold() for other in others)
    ]
    if others and all(vendor.price_from_kzt < other.price_from_kzt for other in others):
        facts.append(Fact("lowest_price", "Среди показанных вариантов здесь самая низкая цена от."))
    if (
        others
        and vendor.max_hours is not None
        and all(
            other.max_hours is not None and vendor.max_hours > other.max_hours for other in others
        )
    ):
        facts.append(
            Fact(
                "longest_duration",
                f"Среди показанных вариантов наибольший предел работы: до {vendor.max_hours} ч.",
            )
        )
    if not facts:
        wording = (
            "Это единственный профиль, прошедший заданные условия."
            if not others
            else "Подтверждённого отличия от показанных вариантов по этим условиям в каталоге нет."
        )
        facts.append(Fact("equal_fit", wording))
    return facts
