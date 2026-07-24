"""Analytics DTOs (F11) — historical KPIs, trends, delivery performance."""

from pydantic import BaseModel


class TrendPoint(BaseModel):
    date: str  # YYYY-MM-DD (UTC day)
    deliveries_completed: int
    deliveries_failed: int
    routes: int
    distance_m: float


class TrendsOut(BaseModel):
    days: int
    points: list[TrendPoint]


class FailureReason(BaseModel):
    reason: str
    count: int


class DriverStat(BaseModel):
    driver_id: str
    driver_name: str
    delivered: int
    failed: int


class PerformanceOut(BaseModel):
    range_days: int
    delivered: int
    failed: int
    success_rate: float  # delivered / (delivered + failed), 0..1
    total_distance_m: float
    routes: int
    avg_distance_per_route_m: float
    failure_reasons: list[FailureReason]
    drivers: list[DriverStat]
