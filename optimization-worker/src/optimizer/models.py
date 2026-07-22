"""Domain models for the solver (docs/RULES.md §5.2 mirrors these names)."""

from __future__ import annotations

from dataclasses import dataclass, field

from optimizer.costs import ObjectiveWeights


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
    demand: float = 0  # weight or volume unit used for capacity dimension
    service_time: int = 300  # seconds
    priority: int = 1
    time_window: tuple[int, int] | None = None  # (start, end) seconds from midnight


@dataclass
class Vehicle:
    id: str
    capacity: float
    depot: GeoPoint
    vehicle_type: str = "car"  # drives fuel/CO2 factors (F14)


@dataclass
class VRPProblem:
    depot: GeoPoint
    deliveries: list[Delivery]
    vehicles: list[Vehicle]
    respect_time_windows: bool = True
    respect_capacity: bool = True
    objective: ObjectiveWeights = field(default_factory=ObjectiveWeights)  # F14


def depot_layout(problem: VRPProblem) -> tuple[list[GeoPoint], list[int]]:
    """Node layout for (multi-)depot VRP (F12): depot nodes first, then deliveries.

    Returns ``(depot_points, depot_index_per_vehicle)``. Vehicles departing from
    the same location share one depot node. The distance matrix must be built over
    ``depot_points + delivery points`` in that order, so a delivery at
    ``problem.deliveries[i]`` is matrix node ``len(depot_points) + i``. With a
    single shared depot this collapses to the classic node-0 depot layout.
    """
    depot_points: list[GeoPoint] = []
    index_by_key: dict[tuple[float, float], int] = {}
    per_vehicle: list[int] = []
    for v in problem.vehicles:
        key = (round(v.depot.lat, 6), round(v.depot.lon, 6))
        idx = index_by_key.get(key)
        if idx is None:
            idx = len(depot_points)
            index_by_key[key] = idx
            depot_points.append(v.depot)
        per_vehicle.append(idx)
    return depot_points, per_vehicle


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
    fuel_l: float = 0  # F14
    co2_kg: float = 0  # F14


@dataclass
class VRPSolution:
    routes: list[VehicleRoute] = field(default_factory=list)
    total_distance_m: float = 0
    total_time_s: int = 0
    total_fuel_l: float = 0  # F14
    total_co2_kg: float = 0  # F14
    objective_value: int = 0
    strategy: str = "or_tools"  # or_tools | greedy_fallback | decomposition
    is_suboptimal: bool = False
