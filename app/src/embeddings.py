"""Semantic closeness of the order to descriptions: ranks feed the score, never the filters."""

import logging
import math

from src.config import settings
from src.errors import UpstreamError
from src.llm import fetch_embeddings
from src.models import Vendor
from src.schemas import RecommendIn

logger = logging.getLogger(__name__)
TOP_RANKS = 3


def get_query_text(order: RecommendIn) -> str:
    parts = [f"{order.category.label} для мероприятия «{order.event_format.label}»"]
    if order.languages:
        parts.append("языки: " + ", ".join(language.label for language in order.languages))
    if order.duration_hours:
        parts.append(f"{order.duration_hours} часов на площадке")
    return ", ".join(parts)


async def fetch_query_embedding(order: RecommendIn) -> list[float] | None:
    if not settings.openai_api_key:
        return None
    try:
        return (await fetch_embeddings([get_query_text(order)]))[0]
    except UpstreamError as error:
        logger.warning("description ranks skipped, scoring uses the format regex only: %s", error)
        return None


def get_cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    return dot / norm if norm else 0.0


def get_description_ranks(vendors: list[Vendor], query_embedding: list[float] | None) -> dict:
    """Vendor id -> 1..3 for the descriptions closest to the order. Empty without embeddings."""
    if query_embedding is None:
        return {}
    # Rounded to 3 decimals: a re-embedded query differs in the far digits and must not flip ranks.
    scored = sorted(
        (
            (
                round(get_cosine_similarity(vendor.description_embedding, query_embedding), 3),
                vendor.id,
            )
            for vendor in vendors
            if vendor.description_embedding
        ),
        key=lambda pair: (-pair[0], pair[1]),
    )
    return {vendor_id: rank for rank, (_, vendor_id) in enumerate(scored[:TOP_RANKS], start=1)}
