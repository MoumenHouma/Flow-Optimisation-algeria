"""Greedy fallback strategy (docs/ARCHITECTURE.md §2.3 Fallback Strategy).

Nearest-neighbor construction; a 2-opt local-search pass is a TODO. Used when
OR-Tools times out or returns no solution, flagged as sub-optimal.
"""

from __future__ import annotations

from optimizer.distance_matrix import DistanceMatrix
from optimizer.models import RouteStop, VehicleRoute, VRPProblem, VRPSolution


def greedy_nearest_neighbor(problem: VRPProblem, matrix: DistanceMatrix) -> VRPSolution:
    """Assign deliveries to vehicles round-robin, each visiting nearest-unvisited."""
    unvisited = set(range(1, len(problem.deliveries) + 1))  # node indices (depot=0)
    solution = VRPSolution(strategy="greedy_fallback", is_suboptimal=True)

    for vehicle in problem.vehicles:
        if not unvisited:
            break
        current = 0  # depot
        stops: list[RouteStop] = []
        distance = 0.0
        capacity_left = vehicle.capacity
        seq = 0
        while unvisited:
            candidates = [
                n
                for n in unvisited
                if not problem.respect_capacity or problem.deliveries[n - 1].demand <= capacity_left
            ]
            if not candidates:
                break
            nxt = min(candidates, key=lambda n: matrix.distances[current][n])
            distance += matrix.distances[current][nxt]
            capacity_left -= problem.deliveries[nxt - 1].demand
            stops.append(RouteStop(delivery_id=problem.deliveries[nxt - 1].id, sequence=seq))
            seq += 1
            unvisited.remove(nxt)
            current = nxt
        if stops:
            distance += matrix.distances[current][0]  # return to depot
            solution.routes.append(
                VehicleRoute(vehicle_id=vehicle.id, stops=stops, total_distance_m=distance)
            )
            solution.total_distance_m += distance

    # TODO: 2-opt refinement per route to trim crossings.
    return solution
