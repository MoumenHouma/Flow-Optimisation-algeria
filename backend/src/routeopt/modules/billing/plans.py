"""Plan catalogue (F19) — the single source of truth for tier pricing and caps.

Mirrors PRD §5.1. ``None`` cap = unlimited (Enterprise). Prices in DZD/month.
Changing a company's plan copies these values onto the company row so quota
enforcement (fleet / orders) reads authoritative caps from the DB.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanSpec:
    price_da: float
    max_vehicles: int | None
    max_deliveries_per_day: int | None


PLAN_SPECS: dict[str, PlanSpec] = {
    "free": PlanSpec(price_da=0, max_vehicles=1, max_deliveries_per_day=10),
    "starter": PlanSpec(price_da=2500, max_vehicles=5, max_deliveries_per_day=100),
    "pro": PlanSpec(price_da=7500, max_vehicles=20, max_deliveries_per_day=500),
    # Enterprise pricing is "sur devis" — unlimited caps, amount agreed per deal.
    "enterprise": PlanSpec(price_da=0, max_vehicles=None, max_deliveries_per_day=None),
}

PLANS = tuple(PLAN_SPECS.keys())
