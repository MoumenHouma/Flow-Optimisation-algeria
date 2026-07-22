"""Solver tests (docs/RULES.md §5.2). Uses a synthetic matrix — no OSRM needed."""

from optimizer.costs import ObjectiveWeights
from optimizer.distance_matrix import DistanceMatrix
from optimizer.models import Delivery, GeoPoint, Vehicle, VRPProblem
from optimizer.solver import VRPSolver


def _simple_problem() -> VRPProblem:
    depot = GeoPoint(36.7538, 3.0588)
    return VRPProblem(
        depot=depot,
        deliveries=[
            Delivery(id="1", lat=36.75, lon=3.06, demand=1),
            Delivery(id="2", lat=36.76, lon=3.07, demand=1),
        ],
        vehicles=[Vehicle(id="v1", capacity=10, depot=depot)],
        respect_time_windows=False,
    )


def _matrix_3x3() -> DistanceMatrix:
    d = [[0, 100, 200], [100, 0, 150], [200, 150, 0]]
    return DistanceMatrix(durations=d, distances=d)


def test_solve_returns_valid_solution() -> None:
    solution = VRPSolver(time_limit_seconds=5).solve(_simple_problem(), _matrix_3x3())
    assert solution.routes
    assert solution.total_distance_m > 0
    # both deliveries are served
    served = {s.delivery_id for r in solution.routes for s in r.stops}
    assert served == {"1", "2"}


def _multi_depot_problem() -> VRPProblem:
    # Two depots far apart, each with one nearby delivery.
    depot_a = GeoPoint(36.75, 3.05)
    depot_b = GeoPoint(36.80, 3.20)
    return VRPProblem(
        depot=depot_a,
        deliveries=[
            Delivery(id="near_a", lat=36.75, lon=3.06, demand=1),
            Delivery(id="near_b", lat=36.80, lon=3.21, demand=1),
        ],
        vehicles=[
            Vehicle(id="va", capacity=10, depot=depot_a),
            Vehicle(id="vb", capacity=10, depot=depot_b),
        ],
        respect_time_windows=False,
    )


def _matrix_multi_depot() -> DistanceMatrix:
    # Nodes: 0=depot A, 1=depot B, 2=near_a, 3=near_b.
    d = [
        [0, 2000, 100, 2000],
        [2000, 0, 2000, 100],
        [100, 2000, 0, 1900],
        [2000, 100, 1900, 0],
    ]
    return DistanceMatrix(durations=d, distances=d)


def test_multi_depot_each_vehicle_serves_its_own_area() -> None:
    solution = VRPSolver(time_limit_seconds=5).solve(_multi_depot_problem(), _matrix_multi_depot())
    by_vehicle = {r.vehicle_id: [s.delivery_id for s in r.stops] for r in solution.routes}
    # Each vehicle starts at its own depot and serves the nearby stop.
    assert by_vehicle.get("va") == ["near_a"]
    assert by_vehicle.get("vb") == ["near_b"]


def _eco_problem(objective: ObjectiveWeights) -> VRPProblem:
    # One delivery, two vehicles at the same depot: a truck and a motorcycle.
    depot = GeoPoint(36.7538, 3.0588)
    return VRPProblem(
        depot=depot,
        deliveries=[Delivery(id="1", lat=36.75, lon=3.06, demand=1)],
        vehicles=[
            Vehicle(id="truck", capacity=100, depot=depot, vehicle_type="truck"),
            Vehicle(id="moto", capacity=100, depot=depot, vehicle_type="motorcycle"),
        ],
        respect_time_windows=False,
        objective=objective,
    )


def test_eco_objective_prefers_greener_vehicle() -> None:
    matrix = _matrix_3x3()  # nodes: depot, d1, (unused d2 row kept for shape)
    solver = VRPSolver(time_limit_seconds=5)

    # Distance-only: fuel/CO2 ignored, cost identical for both vehicles.
    dist_only = solver.solve(_eco_problem(ObjectiveWeights(distance=1.0)), matrix)
    assert {s.delivery_id for r in dist_only.routes for s in r.stops} == {"1"}

    # Eco weighting (fuel + CO2) makes the truck more expensive → the moto serves it.
    eco = solver.solve(_eco_problem(ObjectiveWeights(distance=0.0, fuel=1.0, co2=1.0)), matrix)
    served_by = {r.vehicle_id for r in eco.routes for s in r.stops}
    assert served_by == {"moto"}
    # The breakdown is populated.
    route = next(r for r in eco.routes if r.stops)
    assert route.fuel_l > 0
    assert route.co2_kg > 0
