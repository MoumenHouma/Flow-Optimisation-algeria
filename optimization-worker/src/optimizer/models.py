"""Domain models for the solver (docs/RULES.md §5.2 mirrors these names)."""

from __future__ import annotations

from dataclasses import dataclass, field


class OptimizationError(Exception):
    """Raised when a problem is infeasible or the solver fails."""


class ORToolsTimeoutError(OptimizationError):
    """Raised when OR-Tools exhausts its time limit without a solution."""


@dataclass(frozen=True)
class GeoPoint:
    lat: float
    lon: float


@dataclass
class Delivery:
    id: str
    lat: float
    lon: float
    demand: float = 0            # weight or volume unit used for capacity dimension
    service_time: int = 300      # seconds
    priority: int = 1
    time_window: tuple[int, int] | None = None  # (start, end) seconds from midnight


@dataclass
class Vehicle:
    id: str
    capacity: float
    depot: GeoPoint


@dataclass
class VRPProblem:
    depot: GeoPoint
    deliveries: list[Delivery]
    vehicles: list[Vehicle]
    respect_time_windows: bool = True
    respect_capacity: bool = True


@dataclass
class RouteStop:
    delivery_id: str
    sequence: int
    eta_s: int | None = None


@dataclass
class VehicleRoute:
    vehicle_id: str
    stops: list[RouteStop]
    total_distance_m: float = 0
    total_time_s: int = 0


@dataclass
class VRPSolution:
    routes: list[VehicleRoute] = field(default_factory=list)
    total_distance_m: float = 0
    total_time_s: int = 0
    objective_value: int = 0
    strategy: str = "or_tools"      # or_tools | greedy_fallback | decomposition
    is_suboptimal: bool = False
