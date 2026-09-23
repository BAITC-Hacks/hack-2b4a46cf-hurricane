"""Hard filters: a vendor passes every condition of the order or is counted under one reason."""

from collections import Counter

from src.models import Vendor
from src.schemas import RecommendIn, RejectionOut

# Order matters: a vendor is counted under its first failed check, so counts sum to the pool.
REASON_ORDER = ("busy", "format", "budget", "duration", "language")


def get_rejection_reasons(vendor: Vendor, order: RecommendIn) -> list[str]:
    checks = {
        "busy": order.event_date in vendor.busy_dates,
        "format": order.event_format not in vendor.event_formats,
        "budget": vendor.price_from_kzt > order.budget_kzt,
        "duration": bool(order.duration_hours)
        and vendor.max_hours is not None
        and vendor.max_hours < order.duration_hours,
        "language": not set(order.languages) <= set(vendor.languages),
    }
    return [reason for reason in REASON_ORDER if checks[reason]]


def get_rejections(pool: list[Vendor], order: RecommendIn) -> list[RejectionOut]:
    first_reasons = Counter(
        reasons[0] for vendor in pool if (reasons := get_rejection_reasons(vendor, order))
    )
    return [
        RejectionOut(reason=r, count=first_reasons[r]) for r in REASON_ORDER if first_reasons[r]
    ]
