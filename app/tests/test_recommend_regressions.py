"""Reproduce duplicate explanations and city hints through the recommendation endpoint."""

import asyncio
import json
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src import explain, recommend
from src.errors import UpstreamError
from src.models import Vendor
from src.schemas import RecommendIn
from src.seed import read_vendor_rows


@pytest.fixture
def request_catalog(monkeypatch):
    vendors = [Vendor(**row) for row in read_vendor_rows()]

    async def fetch_pool(_session, order):
        return [v for v in vendors if v.city == order.city and order.category in v.categories]

    monkeypatch.setattr(recommend, "fetch_pool", fetch_pool)
    monkeypatch.setattr(explain, "fetch_llm_json", AsyncMock(return_value={}))

    def request(**conditions):
        order = RecommendIn.model_validate(
            {
                "city": "almaty",
                "event_format": "wedding",
                "budget_kzt": 1_500_000,
                **conditions,
            }
        )
        candidates = [v for v in vendors if v.city != order.city and order.category in v.categories]
        session = SimpleNamespace(scalars=AsyncMock(return_value=candidates))
        return asyncio.run(recommend.recommend(order, session))

    return request


def get_model_response(mode, prompt):
    vendors = json.loads(prompt)["vendors"]
    if mode == "unavailable":
        raise UpstreamError("local test: model unavailable")
    if mode == "malformed":
        raise ValueError("local test: invalid JSON")
    if mode == "empty":
        return {}
    selections = {}
    for index, vendor in enumerate(vendors):
        fact_id = vendor["facts"][0]["id"]
        if mode == "unknown":
            fact_id = "not-a-fact"
        if mode == "foreign":
            fact_id = vendors[(index + 1) % len(vendors)]["facts"][0]["id"]
        selections[vendor["id"]] = fact_id
    return {"selected_facts": selections, "explanation": "Выдуманный рекламный текст"}


@pytest.mark.parametrize(
    "mode", ["unavailable", "malformed", "empty", "unknown", "foreign", "valid"]
)
@pytest.mark.parametrize(
    "category,day,expected_ids,details",
    [
        (
            "host",
            "2026-10-27",
            ["HK-35215", "HK-27222", "HK-77838"],
            {"HK-27222": "опыт более 12 лет", "HK-77838": "актер театра и кино"},
        ),
        (
            "live-band",
            "2026-09-23",
            ["HK-23752", "HK-57480", "HK-83709"],
            {"HK-23752": "два вокалиста", "HK-83709": "4 вокалиста"},
        ),
    ],
)
def test_distinct_explanations_and_safe_fallback(
    request_catalog,
    monkeypatch,
    mode,
    category,
    day,
    expected_ids,
    details,
):
    async def fetch_model(_system, prompt):
        return get_model_response(mode, prompt)

    monkeypatch.setattr(explain, "fetch_llm_json", fetch_model)
    first = request_catalog(category=category, event_date=day)
    second = request_catalog(category=category, event_date=day)
    assert [card.id for card in first.cards] == expected_ids
    assert second == first
    cards = {card.id: card for card in first.cards}
    for vendor_id, detail in details.items():
        assert detail in cards[vendor_id].explanation
    assert len({cards[vendor_id].explanation for vendor_id in details}) == len(details)
    for card in first.cards:
        assert len(re.split(r"(?<=[.!?])\s+(?=[А-Я])", card.explanation)) == 2
        assert all(name not in card.explanation for name in (c.name for c in first.cards))
        assert "цена от" in card.explanation
        assert not any(word in card.explanation for word in ("хватит", "переработ", "рекламный"))
        assert card.explanation_source == ("llm" if mode == "valid" else "template")


@pytest.mark.parametrize(
    "conditions,expected",
    [
        ({}, [("almaty", 1), ("astana", 1)]),
        ({"budget_kzt": 200_000}, []),
        ({"languages": ["kk", "ru"]}, [("almaty", 1)]),
        ({"languages": ["en"]}, []),
        ({"event_format": "conference"}, [("astana", 1)]),
        ({"event_date": "2026-11-21"}, []),
        ({"duration_hours": 24}, [("almaty", 1), ("astana", 1)]),
    ],
)
def test_city_counts_match_all_filters(request_catalog, conditions, expected):
    order = {"category": "florist", "event_date": "2026-11-14", "budget_kzt": 300_000, **conditions}
    response = request_catalog(city="abroad", **order)
    assert response.outcome == "no_category_in_city"
    assert response.pool_size == response.passed_count == 0
    assert [(hint.city, hint.count) for hint in response.suggestions] == expected
    for city in ("almaty", "astana"):
        actual = request_catalog(city=city, **order)
        assert dict(expected).get(city, 0) == actual.passed_count


def test_city_counts_respect_known_duration_limits(request_catalog):
    order = {
        "category": "host",
        "event_date": "2026-10-27",
        "duration_hours": 9,
        "languages": ["ru", "kk"],
    }
    response = request_catalog(city="abroad", **order)
    assert [(hint.city, hint.count) for hint in response.suggestions] == [("almaty", 2)]
    for hint in response.suggestions:
        actual = request_catalog(city=hint.city, **order)
        assert hint.count == actual.passed_count
        assert all(card.max_hours is None or card.max_hours >= 9 for card in actual.cards)


@pytest.mark.parametrize(
    "category,day,choices,details",
    [
        (
            "host",
            "2026-10-27",
            {"HK-77838": "duration:8"},
            {"HK-77838": "предел работы до 8 ч"},
        ),
        (
            "live-band",
            "2026-09-23",
            {
                "HK-23752": "description:lineup:труба:unspecified",
                "HK-83709": "description:lineup:струнный квартет:unspecified",
            },
            {"HK-23752": "«труба»", "HK-83709": "«струнный квартет»"},
        ),
    ],
)
def test_other_verified_choices_preserve_order(
    request_catalog, monkeypatch, category, day, choices, details
):
    baseline = request_catalog(category=category, event_date=day)

    async def fetch_model(_system, prompt):
        vendors = json.loads(prompt)["vendors"]
        for vendor in vendors:
            own_ids = {fact["id"] for fact in vendor["facts"]}
            others = {fact["id"] for other in vendors if other != vendor for fact in other["facts"]}
            assert not own_ids & others
        return {"selected_facts": choices}

    monkeypatch.setattr(explain, "fetch_llm_json", fetch_model)
    response = request_catalog(category=category, event_date=day)
    assert [card.id for card in response.cards] == [card.id for card in baseline.cards]
    for card in response.cards:
        if card.id in details:
            assert card.explanation_source == "llm"
            assert details[card.id] in card.explanation
