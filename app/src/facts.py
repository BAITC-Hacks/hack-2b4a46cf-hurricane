"""Extract conservative, source-backed distinctions for recommendation cards."""

import re
from dataclasses import dataclass

from src.models import Vendor
from src.schemas import Language


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
EXPERIENCE_PATTERN = re.compile(
    r"\bопыт(?:ом)?(?P<scope> работы| ведения свадеб)?\s+"
    r"(?P<qualifier>более |свыше |от )?(?P<years>\d{1,2})\s+(?P<unit>лет|года?|годов)\b"
)
ROLE_PATTERNS = (
    ("actor", r"актер (?:театра и кино|кино и театра|театра|кино)"),
    ("acting_teacher", r"(?:педагог|преподаватель) по актерскому мастерству"),
    ("tv_presenter", r"телеведущий"),
)
COUNT_WORDS = {"один": 1, "одна": 1, "два": 2, "две": 2, "три": 3, "четыре": 4}
LINEUP_PATTERN = re.compile(
    r"(?<![\w-])(?:(?P<count>\d{1,2}|один|одна|два|две|три|четыре)\s+)?"
    r"(?P<role>вокалист(?:ка|ки|ок|ы|ов|а)?|струнный квартет|духовой брасс|"
    r"перкуссионист|клавишник|барабанщик|бас-гитарист|соло-гитарист|гитарист|"
    r"труба|саксофон|тромбон)(?![\w-])"
)


def get_affirmative_clauses(description: str) -> list[str]:
    clauses = re.split(r"[.!?;\n]", description.casefold().replace("ё", "е"))
    # A negation or optional offer is not evidence of an included service or experience.
    return [
        clause
        for clause in clauses
        if not re.search(r"\b(?:не|нет|без|может|могут|возможно|возможен|возможна)\b", clause)
    ]


def get_lineup_facts(clause: str) -> list[Fact]:
    lineup = re.search(r"\bсостав[^:]*:\s*([^.!?]+)", clause)
    if not lineup:
        return []
    facts = []
    for match in LINEUP_PATTERN.finditer(lineup[1]):
        role = match["role"]
        if role.startswith("вокалист"):
            role = "вокалистка" if "к" in role.removeprefix("вокалист") else "вокалист"
        count = match["count"] or "unspecified"
        count = COUNT_WORDS.get(count, count)
        facts.append(
            Fact(
                f"description:lineup:{role}:{count}",
                f"В описании состава указано: «{match[0]}».",
            )
        )
    return facts


def get_description_facts(vendor: Vendor) -> list[Fact]:
    clauses = get_affirmative_clauses(vendor.description)
    facts = [
        Fact(f"description:{phrase}", wording)
        for phrase, wording in DESCRIPTION_FACTS
        if any(phrase in clause for clause in clauses)
    ]
    for clause in clauses:
        for match in EXPERIENCE_PATTERN.finditer(clause):
            scope = "wedding" if match["scope"] == " ведения свадеб" else "general"
            qualifier = {"более ": "over", "свыше ": "over", "от ": "from"}.get(
                match["qualifier"], "exact"
            )
            facts.append(
                Fact(
                    f"description:experience:{scope}:{qualifier}:{int(match['years'])}",
                    f"В описании указан опыт{match['scope'] or ''} "
                    f"{match['qualifier'] or ''}{match['years']} {match['unit']}.",
                )
            )
        for role, pattern in ROLE_PATTERNS:
            if match := re.search(rf"\b{pattern}\b", clause):
                facts.append(Fact(f"description:role:{role}", f"В описании указано: «{match[0]}»."))
        facts.extend(get_lineup_facts(clause))
    return facts


def get_duration_facts(vendor: Vendor, others: list[Vendor]) -> list[Fact]:
    if vendor.max_hours is None or any(vendor.max_hours == other.max_hours for other in others):
        return []
    if others and all(
        other.max_hours is not None and vendor.max_hours > other.max_hours for other in others
    ):
        return [
            Fact(
                "longest_duration",
                f"Среди показанных вариантов наибольший предел работы: до {vendor.max_hours} ч.",
            )
        ]
    return [
        Fact(
            f"duration:{vendor.max_hours}",
            f"В каталоге указан предел работы до {vendor.max_hours} ч; "
            "время программы нужно согласовать.",
        )
    ]


def get_structured_facts(vendor: Vendor, others: list[Vendor]) -> list[Fact]:
    facts = []
    if others and all(vendor.price_from_kzt < other.price_from_kzt for other in others):
        facts.append(Fact("lowest_price", "Среди показанных вариантов здесь самая низкая цена от."))
    facts.extend(get_duration_facts(vendor, others))
    other_languages = {language for other in others for language in other.languages}
    for language in sorted(set(vendor.languages) - other_languages):
        facts.append(
            Fact(
                f"language:{language}",
                f"В каталоге также указан язык работы: {Language(language).label}.",
            )
        )
    return facts


def get_vendor_facts(vendor: Vendor, shown: list[Vendor]) -> list[Fact]:
    others = [other for other in shown if other.id != vendor.id]
    other_fact_ids = {fact.id for other in others for fact in get_description_facts(other)}
    facts = [fact for fact in get_description_facts(vendor) if fact.id not in other_fact_ids]
    facts.extend(get_structured_facts(vendor, others))
    if not facts:
        wording = (
            "Это единственный профиль, прошедший заданные условия."
            if not others
            else "Подтверждённого отличия от показанных вариантов по этим условиям в каталоге нет."
        )
        facts.append(Fact("equal_fit", wording))
    return facts
