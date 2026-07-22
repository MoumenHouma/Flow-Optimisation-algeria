"""VRP solver wrapping OR-Tools with a fallback (docs/RULES.md §2.2, ARCHITECTURE §2.3).

Nodes 0..D-1 are depots and D..D+N-1 map to problem.deliveries[node-D] (F12
multi-dépôt: each vehicle starts and ends at its own depot node; D=1 is the
classic single-depot case). Dimensions: Distance (minimize), Time (+slack for
time windows), Capacity (unary demand).
"""

from __future__ import annotations

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from collections.abc import Callable

from optimizer.costs import EmissionFactors, arc_cost, co2_g, factors_for, fuel_ml
from optimizer.distance_matrix import DistanceMatrix
from optimizer.fallback import greedy_nearest_neighbor
from optimizer.models import (
    ORToolsTimeoutError,
    OptimizationError,
    RouteStop,
    VehicleRoute,
    VRPProblem,
    VRPSolution,
    depot_layout,
)


class VRPSolver:
    def __init__(
        self,
        time_limit_seconds: int = 30,
        first_solution_strategy: int = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
        metaheuristic: int = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
    ) -> None:
        self.time_limit = time_limit_seconds
        self.first_strategy = first_solution_strategy
        self.metaheuristic = metaheuristic

    def solve(self, problem: VRPProblem, matrix: DistanceMatrix) -> VRPSolution:
        """Solve VRP with OR-Tools, falling back to greedy on timeout."""
        try:
            return self._solve_with_ortools(problem, matrix)
        except ORToolsTimeoutError:
            solution = greedy_nearest_neighbor(problem, matrix)
            solution.is_suboptimal = True
            solution.strategy = "greedy_fallback"
            return solution

    def _search_parameters(self) -> pywrapcp.RoutingSearchParameters:
        params = pywrapcp.DefaultRoutingSearchParameters()
        params.first_solution_strategy = self.first_strategy
        params.local_search_metaheuristic = self.metaheuristic
        params.time_limit.seconds = self.time_limit
        params.log_search = False
        return params

    def _solve_with_ortools(self, problem: VRPProblem, matrix: DistanceMatrix) -> VRPSolution:
        depot_points, depot_of_vehicle = depot_layout(problem)
        num_depots = len(depot_points)
        num_nodes = num_depots + len(problem.deliveries)
        num_vehicles = len(problem.vehicles)

        # Each vehicle starts and ends at its own depot node (F12 multi-dépôt).
        manager = pywrapcp.RoutingIndexManager(
            num_nodes, num_vehicles, depot_of_vehicle, depot_of_vehicle
        )
        routing = pywrapcp.RoutingModel(manager)

        # --- Objective: weighted distance + time + fuel + CO2, per vehicle (F14) ---
        # Default weights (distance=1) make the arc cost identical to meters, so
        # single-objective behaviour is unchanged. Fuel/CO2 depend on vehicle type,
        # so each vehicle gets its own cost evaluator.
        weights = problem.objective
        vehicle_factors = [factors_for(v.vehicle_type) for v in problem.vehicles]

        def make_cost_cb(factors: EmissionFactors) -> Callable[[int, int], int]:
            def cb(from_index: int, to_index: int) -> int:
                f, t = manager.IndexToNode(from_index), manager.IndexToNode(to_index)
                return arc_cost(matrix.distances[f][t], matrix.durations[f][t], factors, weights)

            return cb

        for vi in range(num_vehicles):
            cost_idx = routing.RegisterTransitCallback(make_cost_cb(vehicle_factors[vi]))
            routing.SetArcCostEvaluatorOfVehicle(cost_idx, vi)

        # --- Capacity dimension ---
        if problem.respect_capacity:

            def demand_cb(from_index: int) -> int:
                node = manager.IndexToNode(from_index)
                return 0 if node < num_depots else int(problem.deliveries[node - num_depots].demand)

            demand_idx = routing.RegisterUnaryTransitCallback(demand_cb)
            routing.AddDimensionWithVehicleCapacity(
                demand_idx,
                0,
                [int(v.capacity) for v in problem.vehicles],
                True,
                "Capacity",
            )

        # --- Range dimension (F20 fuel-shortage) ---
        # Cap each vehicle's total route distance at its fuel range so a tank that
        # can't cover the tour is never assigned it. Vehicles without a range get a
        # very high cap (effectively unlimited). Skipped entirely when no vehicle
        # declares a range, to keep the classic problem untouched.
        if any(v.range_m is not None for v in problem.vehicles):
            _UNLIMITED_M = 1_000_000_000

            def range_cb(from_index: int, to_index: int) -> int:
                f, t = manager.IndexToNode(from_index), manager.IndexToNode(to_index)
                return int(matrix.distances[f][t])

            range_idx = routing.RegisterTransitCallback(range_cb)
            caps = [
                int(v.range_m) if v.range_m is not None else _UNLIMITED_M
                for v in problem.vehicles
            ]
            routing.AddDimensionWithVehicleCapacity(range_idx, 0, caps, True, "Range")

        # --- Time dimension with windows ---
        if problem.respect_time_windows:

            def time_cb(from_index: int, to_index: int) -> int:
                f, t = manager.IndexToNode(from_index), manager.IndexToNode(to_index)
                service = 0 if f < num_depots else problem.deliveries[f - num_depots].service_time
                return int(matrix.durations[f][t]) + service

            time_idx = routing.RegisterTransitCallback(time_cb)
            routing.AddDimension(time_idx, 86400, 86400, False, "Time")
            time_dim = routing.GetDimensionOrDie("Time")
            for node, delivery in enumerate(problem.deliveries, start=num_depots):
                if delivery.time_window:
                    index = manager.NodeToIndex(node)
                    time_dim.CumulVar(index).SetRange(*delivery.time_window)

        solution = routing.SolveWithParameters(self._search_parameters())
        if solution is None:
            # No solution within the time limit -> caller applies fallback.
            raise ORToolsTimeoutError("OR-Tools returned no solution within time limit")

        return self._extract_solution(
            problem, num_depots, matrix, vehicle_factors, manager, routing, solution
        )

    def _extract_solution(
        self,
        problem: VRPProblem,
        num_depots: int,
        matrix: DistanceMatrix,
        vehicle_factors: list[EmissionFactors],
        manager: pywrapcp.RoutingIndexManager,
        routing: pywrapcp.RoutingModel,
        assignment: pywrapcp.Assignment,
    ) -> VRPSolution:
        # Arc cost is now the weighted objective, so distance/time are re-summed
        # from the matrix and fuel/CO2 derived per vehicle type (F14 breakdown).
        result = VRPSolution(objective_value=assignment.ObjectiveValue())
        for vehicle_id in range(len(problem.vehicles)):
            index = routing.Start(vehicle_id)
            stops: list[RouteStop] = []
            distance = 0.0
            duration = 0.0
            seq = 0
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if node >= num_depots:  # skip depot nodes
                    stops.append(
                        RouteStop(
                            delivery_id=problem.deliveries[node - num_depots].id, sequence=seq
                        )
                    )
                    seq += 1
                prev = index
                index = assignment.Value(routing.NextVar(index))
                a, b = manager.IndexToNode(prev), manager.IndexToNode(index)
                distance += matrix.distances[a][b]
                duration += matrix.durations[a][b]
            if stops:
                factors = vehicle_factors[vehicle_id]
                route = VehicleRoute(
                    vehicle_id=problem.vehicles[vehicle_id].id,
                    stops=stops,
                    total_distance_m=distance,
                    total_time_s=int(duration),
                    fuel_l=round(fuel_ml(distance, duration, factors) / 1000.0, 3),
                    co2_kg=round(co2_g(distance, duration, factors) / 1000.0, 3),
                )
                result.routes.append(route)
                result.total_distance_m += distance
                result.total_time_s += int(duration)
                result.total_fuel_l = round(result.total_fuel_l + route.fuel_l, 3)
                result.total_co2_kg = round(result.total_co2_kg + route.co2_kg, 3)
        if not result.routes:
            raise OptimizationError("infeasible: no route could be built")
        return result
