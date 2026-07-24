from pydantic import BaseModel, Field


class DashboardSummary(BaseModel):
    """KPIs for the manager dashboard (docs/DESIGN.md §3.2).

    All figures are computed from stored data. There is deliberately no
    "vs manual" comparison — the system has no manual-planning baseline to
    compare against, so we don't fabricate one.
    """

    date: str
    deliveries_total: int
    deliveries_by_status: dict[str, int] = Field(default_factory=dict)
    vehicles_active: int
    vehicles_total: int
    today_routes: int
    today_distance_m: float
    today_time_s: int
    week_optimizations: int
    week_distance_m: float
