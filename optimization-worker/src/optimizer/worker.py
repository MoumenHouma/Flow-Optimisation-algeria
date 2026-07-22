"""Queue consumer: pops optimization jobs from Redis, solves, publishes results.

Flow (docs/ARCHITECTURE.md §3.1): BLPOP queue:optimize -> hydrate problem from
the message payload -> distance matrix (OSRM+cache, haversine fallback) -> solve
-> write result to `opt:result:{job_id}` for the backend to persist on poll.

The worker is intentionally DB-free: the backend enqueues the full problem and
persists the result, so no ORM models are duplicated here.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import redis.asyncio as redis

from optimizer.config import get_settings
from optimizer.distance_matrix import build_matrix_with_fallback, osrm_route_geometry
from optimizer.costs import ObjectiveWeights
from optimizer.models import (
    Delivery,
    GeoPoint,
    OptimizationError,
    Vehicle,
    VRPProblem,
    VRPSolution,
    depot_layout,
)
from optimizer.postprocessor import solution_to_result
from optimizer.preprocessor import cluster, needs_decomposition, validate
from optimizer.solver import VRPSolver

settings = get_settings()

RESULT_KEY = "opt:result:{job_id}"
RESULT_TTL_S = 3600


def _time_limit_for(num_deliveries: int) -> int:
    if num_deliveries < 50:
        return settings.time_limit_small_s
    if num_deliveries < 200:
        return settings.time_limit_medium_s
    return settings.time_limit_large_s


def _build_problem(payload: dict[str, Any]) -> VRPProblem:
    depot = GeoPoint(**payload["depot"])
    deliveries = [
        Delivery(
            id=d["id"],
            lat=d["lat"],
            lon=d["lon"],
            demand=d.get("demand", 0),
            service_time=d.get("service_time", 300),
            priority=d.get("priority", 1),
            time_window=tuple(d["time_window"]) if d.get("time_window") else None,
        )
        for d in payload["deliveries"]
    ]
    vehicles = [
        Vehicle(
            id=v["id"],
            capacity=v["capacity"],
            depot=GeoPoint(v["depot"]["lat"], v["depot"]["lon"]),
            vehicle_type=v.get("vehicle_type", "car"),
            range_m=v.get("range_m"),
        )
        for v in payload["vehicles"]
    ]
    constraints = payload.get("constraints", {})
    obj = payload.get("objective") or {}
    objective = ObjectiveWeights(
        distance=obj.get("distance", 1.0),
        time=obj.get("time", 0.0),
        fuel=obj.get("fuel", 0.0),
        co2=obj.get("co2", 0.0),
    )
    return VRPProblem(
        depot=depot,
        deliveries=deliveries,
        vehicles=vehicles,
        respect_time_windows=constraints.get("respect_time_windows", True),
        respect_capacity=constraints.get("respect_capacity", True),
        objective=objective,
    )


async def _solve_one(
    problem: VRPProblem, redis_client: redis.Redis
) -> tuple[VRPSolution, bool, dict[str, dict[str, Any]]]:
    """Build the matrix, solve one (sub-)problem, and render its route geometry."""
    # Matrix nodes: depot(s) first, then deliveries — same layout the solver uses.
    depot_points, _ = depot_layout(problem)
    points = depot_points + [GeoPoint(d.lat, d.lon) for d in problem.deliveries]
    matrix, used_osrm = await build_matrix_with_fallback(points, redis_client)

    solver = VRPSolver(time_limit_seconds=_time_limit_for(len(problem.deliveries)))
    solution = solver.solve(problem, matrix)

    geometries: dict[str, dict[str, Any]] = {}
    if used_osrm:
        coords = {d.id: GeoPoint(d.lat, d.lon) for d in problem.deliveries}
        depot_by_vehicle = {v.id: v.depot for v in problem.vehicles}
        for route in solution.routes:
            ordered = sorted(route.stops, key=lambda s: s.sequence)
            home = depot_by_vehicle.get(route.vehicle_id, problem.depot)
            pts = [home, *[coords[s.delivery_id] for s in ordered], home]
            geom = await osrm_route_geometry(pts)
            if geom is not None:
                geometries[route.vehicle_id] = geom
    return solution, used_osrm, geometries


def _merge_into(acc: VRPSolution, part: VRPSolution) -> None:
    """Fold a sub-problem's solution into the aggregate (routes + totals)."""
    acc.routes.extend(part.routes)
    acc.total_distance_m += part.total_distance_m
    acc.total_time_s += part.total_time_s
    acc.total_fuel_l = round(acc.total_fuel_l + part.total_fuel_l, 3)
    acc.total_co2_kg = round(acc.total_co2_kg + part.total_co2_kg, 3)
    acc.objective_value += part.objective_value
    acc.is_suboptimal = acc.is_suboptimal or part.is_suboptimal


async def process_job(message: dict[str, Any], redis_client: redis.Redis) -> dict[str, Any]:
    """Process one job payload; return the result message the backend persists."""
    started = time.monotonic()
    job_id = message["job_id"]
    company_id = message.get("company_id")

    try:
        problem = _build_problem(message)
        validate(problem)

        # Large instances (> threshold) are split into geographic sub-problems,
        # solved independently and merged, so each solve stays fast (ARCHITECTURE §4.1).
        subproblems = cluster(problem) if needs_decomposition(problem) else [problem]
        decomposed = len(subproblems) > 1

        solution = VRPSolution(strategy="decomposition" if decomposed else "or_tools")
        geometries: dict[str, dict[str, Any]] = {}
        used_osrm = True
        for sub in subproblems:
            sub_solution, sub_osrm, sub_geom = await _solve_one(sub, redis_client)
            _merge_into(solution, sub_solution)
            geometries.update(sub_geom)
            used_osrm = used_osrm and sub_osrm
        if not used_osrm:
            solution.is_suboptimal = True  # distances are straight-line approximations
        if decomposed:
            solution.strategy = "decomposition"

        duration_ms = int((time.monotonic() - started) * 1000)
        return {
            "job_id": job_id,
            "company_id": company_id,
            "status": "completed",
            "error": None,
            "used_osrm": used_osrm,
            **solution_to_result(solution, duration_ms, geometries),
        }
    except OptimizationError as exc:
        return {
            "job_id": job_id,
            "company_id": company_id,
            "status": "failed",
            "error": str(exc),
            "duration_ms": int((time.monotonic() - started) * 1000),
            "routes": [],
        }


async def _publish_result(redis_client: redis.Redis, result: dict[str, Any]) -> None:
    await redis_client.set(
        RESULT_KEY.format(job_id=result["job_id"]), json.dumps(result), ex=RESULT_TTL_S
    )


async def run() -> None:
    redis_client: redis.Redis = redis.from_url(settings.redis_url, decode_responses=True)
    print(f"[optimizer] listening on {settings.optimize_queue}")  # noqa: T201
    while True:
        item = await redis_client.blpop([settings.optimize_queue], timeout=5)
        if item is None:
            continue
        _, raw = item
        message = json.loads(raw)
        result = await process_job(message, redis_client)
        await _publish_result(redis_client, result)
        print(f"[optimizer] job {result['job_id']} -> {result['status']}")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(run())
