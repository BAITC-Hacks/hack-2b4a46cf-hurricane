"""Request and response schemas. Validation happens here, once, at the API boundary."""

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Option(StrEnum):
    """Closed catalog set: latin `value` goes to URLs and the DB, `label` is shown to people."""

    label: str

    def __new__(cls, value: str, label: str) -> "Option":
        member = str.__new__(cls, value)
        member._value_ = value
        member.label = label
        return member


class City(Option):
    almaty = "almaty", "Алматы"
    astana = "astana", "Астана"
    abroad = "abroad", "Зарубежье"


class EventFormat(Option):
    wedding = "wedding", "свадьба"
    toi = "toi", "той"
    corporate = "corporate", "корпоратив"
    conference = "conference", "конференция"
    anniversary = "anniversary", "юбилей"
    birthday = "birthday", "день рождения"


class Language(Option):
    ru = "ru", "русский"
    kk = "kk", "казахский"
    en = "en", "английский"

    @property
    def prepositional(self) -> str:
        # "работает на английском", not "на языках: английский".
        return self.label.removesuffix("ий") + "ом"


class Category(Option):
    host = "host", "Ведущий"
    ceremony_host = "ceremony-host", "Ведущий церемонии"
    photographer = "photographer", "Фотограф"
    videographer = "videographer", "Видеограф"
    photo_booth = "photo-booth", "Фото и видеобудки"
    florist = "florist", "Флорист"
    decorator = "decorator", "Декоратор"
    gifts = "gifts", "Подарки и сувениры"
    live_band = "live-band", "Лайв-бэнд"
    instrumentalist = "instrumentalist", "Инструменталист"
    national_ensemble = "national-ensemble", "Национальный ансамбль"
    dance_group = "dance-group", "Танцевальный коллектив"
    show = "show", "Шоу-программа"
    banquet_hall = "banquet-hall", "Банкетный зал"
    restaurant = "restaurant", "Ресторан"
    hotel = "hotel", "Отель"
    country_venue = "country-venue", "Загородная площадка"


Outcome = Literal["matched", "no_category_in_city", "no_candidates_pass"]
Role = Literal["best_match", "best_price", "premium", "alternative"]
RejectReason = Literal["busy", "format", "budget", "duration", "language"]
MatchedOn = Literal["date", "format", "budget", "duration", "language", "description"]
SuggestionKind = Literal["date", "budget", "duration", "city"]

CATALOG_DATE_FROM = date(2026, 9, 23)
CATALOG_DATE_TO = date(2026, 12, 31)


class HealthOut(BaseModel):
    status: str


class OptionOut(BaseModel):
    value: str
    label: str


def get_option(member: Option) -> OptionOut:
    return OptionOut(value=member.value, label=member.label)


def get_options(values: list[str], option: type[Option]) -> list[OptionOut]:
    return [get_option(option(value)) for value in values]


class CatalogOptionsOut(BaseModel):
    cities: list[OptionOut]
    categories: list[OptionOut]
    event_formats: list[OptionOut]
    languages: list[OptionOut]
    date_from: date
    date_to: date


class VendorOut(BaseModel):
    id: str
    name: str
    categories: list[OptionOut]
    city: OptionOut
    price_from_kzt: int
    event_formats: list[OptionOut]
    languages: list[OptionOut]
    max_hours: int | None
    description: str
    synthetic: bool
    price_imputed: bool
    city_imputed: bool


class RecommendIn(BaseModel):
    city: City
    event_date: date
    event_format: EventFormat
    category: Category
    budget_kzt: int = Field(gt=0, le=50_000_000)
    duration_hours: int | None = Field(default=None, ge=1, le=24)
    # Every selected language is required: a mixed toy needs a host fluent in both.
    languages: list[Language] = Field(default_factory=list, max_length=3)

    @field_validator("event_date")
    @classmethod
    def check_event_date_in_catalog(cls, value: date) -> date:
        if not CATALOG_DATE_FROM <= value <= CATALOG_DATE_TO:
            raise ValueError("Календари подрядчиков известны только с 23.09.2026 по 31.12.2026")
        return value

    @field_validator("languages")
    @classmethod
    def remove_duplicate_languages(cls, value: list[Language]) -> list[Language]:
        return sorted(set(value))


class VendorCardOut(BaseModel):
    id: str
    name: str
    categories: list[OptionOut]
    city: OptionOut
    price_from_kzt: int
    languages: list[OptionOut]
    max_hours: int | None
    role: Role
    explanation: str
    explanation_source: Literal["llm", "template"]
    matched_on: list[MatchedOn]
    synthetic: bool
    price_imputed: bool
    city_imputed: bool


class RejectionOut(BaseModel):
    reason: RejectReason
    count: int


class SuggestionOut(BaseModel):
    """A relaxed query that would return more vendors. The frontend can rerun it in one click."""

    kind: SuggestionKind
    count: int
    event_date: date | None = None
    budget_kzt: int | None = None
    duration_hours: int | None = None
    city: City | None = None


class RecommendOut(BaseModel):
    outcome: Outcome
    cards: list[VendorCardOut]
    pool_size: int
    passed_count: int
    rejections: list[RejectionOut]
    suggestions: list[SuggestionOut]
