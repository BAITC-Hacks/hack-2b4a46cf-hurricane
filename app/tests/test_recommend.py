"""Main recommendation scenarios from the Definition of Done, run on the CSV without DB or LLM."""

import asyncio
from datetime import date

import pytest

from src import embeddings, explain, recommend, suggestions
from src.errors import UpstreamError
from src.explain import BANNED_PHRASES
from src.models import Vendor
from src.schemas import RecommendIn
from src.seed import read_vendor_rows

HOST_ORDER = dict(
    city="almaty",
    event_format="wedding",
    category="host",
    budget_kzt=1_500_000,
    duration_hours=6,
    languages=["ru", "kk"],
)


@pytest.fixture
def catalog(monkeypatch):
    vendors = [Vendor(**row) for row in read_vendor_rows()]

    async def fetch_pool(_session, order):
        return [v for v in vendors if v.city == order.city and order.category in v.categories]

    async def fetch_city_suggestions(_session, _order):
        return []

    async def fetch_llm_json(_system, _prompt):
        raise UpstreamError("test: model unavailable")

    async def fetch_query_embedding(_order):
        return None

    monkeypatch.setattr(recommend, "fetch_query_embedding", fetch_query_embedding)
    monkeypatch.setattr(recommend, "fetch_pool", fetch_pool)
    monkeypatch.setattr(recommend, "fetch_city_suggestions", fetch_city_suggestions)
    monkeypatch.setattr(explain, "fetch_llm_json", fetch_llm_json)
    return vendors


def get_recommendation(day: str, **order):
    request = RecommendIn(event_date=date.fromisoformat(day), **order)
    return asyncio.run(recommend.recommend(request, session=None))


def assert_explanations_are_distinct(cards):
    texts = [card.explanation for card in cards]
    assert len(set(texts)) == len(texts)
    for text in texts:
        assert 20 <= len(text) <= 400
        assert not any(phrase in text.lower() for phrase in BANNED_PHRASES)


def test_dense_category_gives_three_cards_with_own_roles(catalog):
    response = get_recommendation("2026-10-17", **HOST_ORDER)
    assert response.outcome == "matched"
    assert (response.pool_size, response.passed_count, len(response.cards)) == (10, 3, 3)
    assert [(r.reason, r.count) for r in response.rejections] == [
        ("busy", 5),
        ("format", 1),
        ("budget", 1),
    ]
    assert len({card.role for card in response.cards}) == 3
    assert "5 из 10" in response.cards[0].explanation
    assert_explanations_are_distinct(response.cards)


def test_busy_december_date_shrinks_the_same_query(catalog):
    response = get_recommendation("2026-12-19", **HOST_ORDER)
    assert response.outcome == "matched"
    assert (response.passed_count, len(response.cards)) == (1, 1)
    assert [(r.reason, r.count) for r in response.rejections] == [("busy", 9)]
    assert "9 из 10" in response.cards[0].explanation
    assert {s.kind for s in response.suggestions} == {"date"}
    assert all(s.count > 1 for s in response.suggestions)


def test_rare_category_shows_how_many_and_why_fewer(catalog):
    response = get_recommendation(
        "2026-10-20", city="almaty", event_format="wedding", category="florist", budget_kzt=400_000
    )
    assert response.outcome == "matched"
    assert (response.pool_size, response.passed_count) == (3, 1)
    assert [(r.reason, r.count) for r in response.rejections] == [("busy", 2)]
    assert "2" in response.cards[0].explanation and "3" in response.cards[0].explanation


def test_candidates_exist_but_none_pass(catalog):
    response = get_recommendation(
        "2026-10-10",
        city="astana",
        event_format="corporate",
        category="photographer",
        budget_kzt=600_000,
    )
    assert response.outcome == "no_candidates_pass"
    assert response.cards == []
    assert (response.pool_size, response.passed_count) == (3, 0)
    assert [(r.reason, r.count) for r in response.rejections] == [("format", 3)]


def test_category_missing_in_city(catalog):
    response = get_recommendation(
        "2026-10-10", city="abroad", event_format="wedding", category="hotel", budget_kzt=600_000
    )
    assert response.outcome == "no_category_in_city"
    assert (response.pool_size, response.passed_count, response.cards) == (0, 0, [])


def test_same_query_gives_same_order(catalog):
    first = get_recommendation("2026-10-17", **HOST_ORDER)
    second = get_recommendation("2026-10-17", **HOST_ORDER)
    assert [c.id for c in first.cards] == [c.id for c in second.cards]
    assert [c.role for c in first.cards] == [c.role for c in second.cards]
    assert [c.explanation for c in first.cards] == [c.explanation for c in second.cards]


def test_passed_vendors_satisfy_every_condition(catalog):
    response = get_recommendation("2026-10-17", **HOST_ORDER)
    by_id = {vendor.id: vendor for vendor in catalog}
    for card in response.cards:
        vendor = by_id[card.id]
        assert date(2026, 10, 17) not in vendor.busy_dates
        assert "wedding" in vendor.event_formats
        assert vendor.price_from_kzt <= 1_500_000
        assert vendor.max_hours is None or vendor.max_hours >= 6
        assert {"ru", "kk"} <= set(vendor.languages)


@pytest.mark.parametrize(
    "answer",
    [
        {},
        {"explanations": "not a dict"},
        {"explanations": {"HK-35215": "Отличный выбор для вашего мероприятия, рекомендуем."}},
        {"explanations": {"HK-35215": "Коротко."}},
        {"explanations": {"HK-35215": "Цена ориентировочная, уточняйте, зато свободен и подходит"}},
    ],
)
def test_bad_llm_answer_falls_back_to_template_without_reordering(catalog, monkeypatch, answer):
    baseline = get_recommendation("2026-10-17", **HOST_ORDER)

    async def fetch_llm_json(_system, _prompt):
        return answer

    monkeypatch.setattr(explain, "fetch_llm_json", fetch_llm_json)
    response = get_recommendation("2026-10-17", **HOST_ORDER)
    assert [c.id for c in response.cards] == [c.id for c in baseline.cards]
    assert all(c.explanation_source == "template" for c in response.cards)
    assert [c.explanation for c in response.cards] == [c.explanation for c in baseline.cards]


def test_valid_llm_text_is_used_only_for_its_card(catalog, monkeypatch):
    text = "Точнее всех попадает в свадьбу: ведёт на казахском и русском, 900 000 ₸ это 60% бюджета"

    async def fetch_llm_json(_system, _prompt):
        return {"explanations": {"HK-35215": text}}

    monkeypatch.setattr(explain, "fetch_llm_json", fetch_llm_json)
    response = get_recommendation("2026-10-17", **HOST_ORDER)
    sources = {card.id: card.explanation_source for card in response.cards}
    assert sources.pop("HK-35215") == "llm"
    assert set(sources.values()) == {"template"}
    assert next(c.explanation for c in response.cards if c.id == "HK-35215") == text


def test_alternative_card_names_its_gap_to_the_best_match(catalog):
    response = get_recommendation("2026-10-17", **HOST_ORDER)
    alternative = next(card for card in response.cards if card.role == "alternative")
    assert any(
        marker in alternative.explanation
        for marker in ("уступает первому", "дешевле первого", "дороже первого", "равен первому")
    )


def test_no_candidates_pass_suggests_cities_where_the_order_passes(catalog):
    order = RecommendIn(
        city="astana",
        event_date=date(2026, 10, 10),
        event_format="corporate",
        category="photographer",
        budget_kzt=600_000,
    )
    other_cities = [v for v in catalog if "photographer" in v.categories and v.city != "astana"]
    hints = suggestions.get_city_suggestions(other_cities, order)
    assert hints and all(s.kind == "city" and s.count > 0 for s in hints)
    assert all(s.city != "astana" for s in hints)


def test_description_ranks_take_top_three_and_break_ties_by_id():
    def vendor(vendor_id, embedding):
        return Vendor(id=vendor_id, description_embedding=embedding)

    vendors = [
        vendor("B", [1.0, 0.0]),
        vendor("A", [1.0, 0.0]),
        vendor("C", [0.0, 1.0]),
        vendor("D", [0.7, 0.7]),
        vendor("E", None),
    ]
    assert embeddings.get_description_ranks(vendors, [1.0, 0.0]) == {"A": 1, "B": 2, "D": 3}
    assert embeddings.get_description_ranks(vendors, None) == {}


def test_closest_description_scores_and_marks_the_card(catalog, monkeypatch):
    hosts = [v for v in catalog if v.city == "almaty" and "host" in v.categories]
    target = next(v for v in hosts if v.id == "HK-77838")
    for vendor in hosts:
        vendor.description_embedding = [1.0, 0.0] if vendor is target else [0.0, 1.0]

    async def fetch_query_embedding(_order):
        return [1.0, 0.0]

    monkeypatch.setattr(recommend, "fetch_query_embedding", fetch_query_embedding)
    response = get_recommendation("2026-10-17", **HOST_ORDER)
    closest = next(card for card in response.cards if card.id == "HK-77838")
    assert "description" in closest.matched_on
    assert "по смыслу" in closest.explanation or closest.role != "best_match"
