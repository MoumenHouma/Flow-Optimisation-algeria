"""Greedy fallback strategy (docs/ARCHITECTURE.md §2.3 Fallback Strategy).

Nearest-neighbor construction; a 2-opt local-search pass is a TODO. Used when
OR-Tools times out or returns no solution, flagged as sub-optimal.
"""

from __future__ import annotations

from optimizer.distance_matrix import DistanceMatrix
from optimizer.models import RouteStop, VehicleRoute, VRPProblem, VRPSolution, depot_layout


def greedy_nearest_neighbor(problem: VRPProblem, matrix: DistanceMatrix) -> VRPSolution:
    """Assign deliveries to vehicles round-robin, each visiting nearest-unvisited.

    Multi-dépôt aware (F12): each vehicle starts and returns to its own depot node.
    """
    depot_points, depot_of_vehicle = depot_layout(problem)
    num_depots = len(depot_points)
    # Delivery node indices sit after the depot nodes.
    unvisited = set(range(num_depots, num_depots + len(problem.deliveries)))
    solution = VRPSolution(strategy="greedy_fallback", is_suboptimal=True)

    for vi, vehicle in enumerate(problem.vehicles):
        if not unvisited:
            break
        home = depot_of_vehicle[vi]
        current = home
        stops: list[RouteStop] = []
        distance = 0.0
        capacity_left = vehicle.capacity
        seq = 0
        while unvisited:
            candidates = [
                n
                for n in unvisited
                if not problem.respect_capacity
                or problem.deliveries[n - num_depots].demand <= capacity_left
            ]
            if not candidates:
                break
            nxt = min(candidates, key=lambda n: matrix.distances[current][n])
            distance += matrix.distances[current][nxt]
            capacity_left -= problem.deliveries[nxt - num_depots].demand
            stops.append(
                RouteStop(delivery_id=problem.deliveries[nxt - num_depots].id, sequence=seq)
            )
            seq += 1
            unvisited.remove(nxt)
            current = nxt
        if stops:
            distance += matrix.distances[current][home]  # return to own depot
            solution.routes.append(
                VehicleRoute(vehicle_id=vehicle.id, stops=stops, total_distance_m=distance)
            )
            solution.total_distance_m += distance

    # TODO: 2-opt refinement per route to trim crossings.
    return solution
