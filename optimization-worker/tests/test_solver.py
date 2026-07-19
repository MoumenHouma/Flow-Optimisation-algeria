"""Solver tests (docs/RULES.md §5.2). Uses a synthetic matrix — no OSRM needed."""

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
