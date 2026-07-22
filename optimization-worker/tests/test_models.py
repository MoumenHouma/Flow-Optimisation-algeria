"""Pure model tests — no OR-Tools/OSRM needed (F12 depot layout)."""

from optimizer.models import Delivery, GeoPoint, Vehicle, VRPProblem, depot_layout


def _problem(vehicle_depots: list[GeoPoint]) -> VRPProblem:
    return VRPProblem(
        depot=vehicle_depots[0],
        deliveries=[Delivery(id="1", lat=36.75, lon=3.06)],
        vehicles=[Vehicle(id=f"v{i}", capacity=10, depot=d) for i, d in enumerate(vehicle_depots)],
    )


def test_single_shared_depot_collapses_to_one_node() -> None:
    a = GeoPoint(36.75, 3.05)
    points, per_vehicle = depot_layout(_problem([a, a]))
    assert len(points) == 1
    assert per_vehicle == [0, 0]


def test_distinct_depots_get_distinct_nodes() -> None:
    a, b = GeoPoint(36.75, 3.05), GeoPoint(36.80, 3.20)
    points, per_vehicle = depot_layout(_problem([a, b, a]))
    assert len(points) == 2
    assert per_vehicle == [0, 1, 0]  # third vehicle shares the first depot node
