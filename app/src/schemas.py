"""Request and response schemas. Validation happens here, once, at the API boundary."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Closed sets taken from the catalog: the frontend gets them as union types via `yarn api:types`.
City = Literal["Алматы", "Астана", "Зарубежье"]
EventFormat = Literal["свадьба", "той", "корпоратив", "конференция", "юбилей", "день рождения"]
Language = Literal["русский", "казахский", "английский"]
Category = Literal[
    "Ведущий",
    "Ведущий церемонии",
    "Фотограф",
    "Видеограф",
    "Фото и видеобудки",
    "Лайв-бэнд",
    "Инструменталист",
    "Национальный ансамбль",
    "Танцевальный коллектив",
    "Шоу-программа",
    "Банкетный зал",
    "Ресторан",
    "Отель",
    "Загородная площадка",
    "Флорист",
    "Декоратор",
    "Подарки и сувениры",
]
Outcome = Literal["matched", "no_category_in_city", "no_candidates_pass"]
Role = Literal["best_match", "best_price", "premium", "alternative"]
RejectReason = Literal["busy", "format", "budget", "duration", "language"]
MatchedOn = Literal["date", "format", "budget", "duration", "language", "description"]
SuggestionKind = Literal["date", "budget", "city"]

CATALOG_DATE_FROM = date(2026, 9, 23)
CATALOG_DATE_TO = date(2026, 12, 31)


class HealthOut(BaseModel):
    status: str


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
    def remove_duplicate_languages(cls, value: list[str]) -> list[str]:
        return sorted(set(value))


class VendorCardOut(BaseModel):
    id: str
    name: str
    categories: list[str]
    city: str
    price_from_kzt: int
    languages: list[str]
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
    city: City | None = None


class RecommendOut(BaseModel):
    outcome: Outcome
    cards: list[VendorCardOut]
    pool_size: int
    rejections: list[RejectionOut]
    suggestions: list[SuggestionOut]
