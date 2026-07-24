"""Greedy fallback strategy (docs/ARCHITECTURE.md §2.3 Fallback Strategy).

Nearest-neighbor construction; a 2-opt local-search pass is a TODO. Used when
OR-Tools times out or returns no solution, flagged as sub-optimal.
"""

from __future__ import annotations

from optimizer.costs import co2_g, factors_for, fuel_ml
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
        duration = 0.0
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
            duration += matrix.durations[current][nxt]
            capacity_left -= problem.deliveries[nxt - num_depots].demand
            stops.append(
                RouteStop(delivery_id=problem.deliveries[nxt - num_depots].id, sequence=seq)
            )
            seq += 1
            unvisited.remove(nxt)
            current = nxt
        if stops:
            distance += matrix.distances[current][home]  # return to own depot
            duration += matrix.durations[current][home]
            factors = factors_for(vehicle.vehicle_type)
            route = VehicleRoute(
                vehicle_id=vehicle.id,
                stops=stops,
                total_distance_m=distance,
                total_time_s=int(duration),
                fuel_l=round(fuel_ml(distance, duration, factors) / 1000.0, 3),
                co2_kg=round(co2_g(distance, duration, factors) / 1000.0, 3),
            )
            solution.routes.append(route)
            solution.total_distance_m += distance
            solution.total_time_s += int(duration)
            solution.total_fuel_l = round(solution.total_fuel_l + route.fuel_l, 3)
            solution.total_co2_kg = round(solution.total_co2_kg + route.co2_kg, 3)

    # TODO: 2-opt refinement per route to trim crossings.
    return solution
