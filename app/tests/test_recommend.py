"""Check the main recommendation scenarios against the unchanged catalog CSV."""

import asyncio
import re
from datetime import date

import pytest

from src import explain, recommend
from src.errors import UpstreamError
from src.models import Vendor
from src.schemas import City, RecommendIn
from src.seed import read_vendor_rows


@pytest.fixture
def catalog(monkeypatch):
    vendors = [Vendor(**row) for row in read_vendor_rows()]

    async def fetch_pool(_session, order):
        return [
            vendor
            for vendor in vendors
            if vendor.city == order.city and order.category in vendor.categories
        ]

    async def fetch_city_suggestions(_session, _order):
        return []

    async def fetch_model(_system, _prompt):
        raise UpstreamError("local test: model unavailable")

    monkeypatch.setattr(recommend, "fetch_pool", fetch_pool)
    monkeypatch.setattr(recommend, "fetch_city_suggestions", fetch_city_suggestions)
    monkeypatch.setattr(explain, "fetch_llm_json", fetch_model)
    return vendors


def get_order(category, day, budget, **conditions):
    return RecommendIn(
        city="almaty",
        event_date=date.fromisoformat(day),
        event_format="wedding",
        category=category,
        budget_kzt=budget,
        **conditions,
    )


def get_recommendation(order):
    return asyncio.run(recommend.recommend(order, session=None))


def assert_verified_cards(cards):
    for card in cards:
        assert len(re.split(r"(?<=[.!?])\s+(?=[А-Я])", card.explanation)) == 2
        assert "цена от" in card.explanation
        assert "хватит" not in card.explanation
        assert "переработ" not in card.explanation
        assert ("оценочная" in card.explanation) == card.price_imputed


def test_florists_have_real_counts_and_distinct_facts(catalog):
    response = get_recommendation(get_order("florist", "2026-11-13", 300_000))
    assert response.outcome == "matched"
    assert response.pool_size == 3
    assert response.passed_count == 2
    assert [(reason.reason, reason.count) for reason in response.rejections] == [("budget", 1)]
    assert {card.id for card in response.cards} == {"HK-39372", "HK-90001"}
    assert any("цветовую палитру" in card.explanation for card in response.cards)
    assert any("цветочное оформление" in card.explanation for card in response.cards)
    assert_verified_cards(response.cards)


def test_short_pool_without_rejections_and_missing_category(catalog):
    two = get_recommendation(get_order("gifts", "2026-09-23", 50_000_000))
    assert two.pool_size == two.passed_count == len(two.cards) == 2
    assert two.rejections == []

    absent = get_order("host", "2026-10-17", 1_500_000).model_copy(update={"city": City.abroad})
    empty = get_recommendation(absent)
    assert empty.outcome == "no_category_in_city"
    assert empty.pool_size == empty.passed_count == 0


def test_ensembles_use_source_details_or_admit_equal_fit(catalog):
    response = get_recommendation(get_order("national-ensemble", "2026-10-09", 500_000))
    cards = {card.id: card for card in response.cards}
    assert {"HK-39301", "HK-92824"} <= cards.keys()
    assert "перед главой государства" in cards["HK-39301"].explanation
    assert "Подтверждённого отличия" in cards["HK-92824"].explanation
    assert cards["HK-39301"].explanation != cards["HK-92824"].explanation
    assert_verified_cards(response.cards)


def test_estimated_prices_and_date_changes(catalog):
    hosts = get_recommendation(get_order("host", "2026-10-11", 1_500_000))
    emilia = next(card for card in hosts.cards if card.id == "HK-42352")
    assert emilia.price_imputed
    assert "оценочная" in emilia.explanation
    for day, expected in (
        ("2026-11-14", ["HK-90001"]),
        ("2026-11-15", ["HK-39372"]),
        ("2026-11-21", []),
    ):
        response = get_recommendation(get_order("florist", day, 300_000))
        assert [card.id for card in response.cards] == expected
        assert response.passed_count == len(expected)
        if not expected:
            assert response.outcome == "no_candidates_pass"
            assert [(reason.reason, reason.count) for reason in response.rejections] == [
                ("busy", 3)
            ]
    chopper = get_recommendation(get_order("florist", "2026-11-15", 300_000)).cards[0]
    assert chopper.price_imputed and "оценочная" in chopper.explanation


def test_extra_conditions_and_repeatability(catalog):
    order = get_order("host", "2026-10-17", 1_500_000, duration_hours=6, languages=["ru", "kk"])
    first = get_recommendation(order)
    second = get_recommendation(order)
    assert [card.id for card in first.cards] == [card.id for card in second.cards]
    assert [card.explanation for card in first.cards] == [card.explanation for card in second.cards]
    by_id = {vendor.id: vendor for vendor in catalog}
    for card in first.cards:
        vendor = by_id[card.id]
        assert {"ru", "kk"} <= set(vendor.languages)
        assert vendor.max_hours is None or vendor.max_hours >= 6
        assert "языки: казахский, русский" in card.explanation
    assert_verified_cards(first.cards)


@pytest.mark.parametrize(
    "answer",
    [
        {},
        {"selected_facts": {"HK-39372": "unknown"}},
        {"selected_facts": {"HK-39372": "description:под цветовую палитру"}},
        {"selected_facts": {"HK-39372": ""}},
    ],
)
def test_invalid_model_selection_falls_back_without_reordering(catalog, monkeypatch, answer):
    order = get_order("florist", "2026-11-13", 300_000)
    baseline = get_recommendation(order)

    async def fetch_model(_system, _prompt):
        return answer

    monkeypatch.setattr(explain, "fetch_llm_json", fetch_model)
    response = get_recommendation(order)
    assert [card.id for card in response.cards] == [card.id for card in baseline.cards]
    assert [card.explanation for card in response.cards] == [
        card.explanation for card in baseline.cards
    ]
    assert all(card.explanation_source == "template" for card in response.cards)
    assert_verified_cards(response.cards)


def test_valid_model_ids_only_select_existing_vendor_facts(catalog, monkeypatch):
    async def fetch_model(_system, _prompt):
        return {"selected_facts": {"HK-39372": "lowest_price"}}

    monkeypatch.setattr(explain, "fetch_llm_json", fetch_model)
    response = get_recommendation(get_order("florist", "2026-11-13", 300_000))
    chopper = next(card for card in response.cards if card.id == "HK-39372")
    assert chopper.explanation_source == "llm"
    assert "самая низкая цена от" in chopper.explanation
    assert_verified_cards(response.cards)
