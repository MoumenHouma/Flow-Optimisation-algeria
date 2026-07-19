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

import redis.asyncio as redis

from optimizer.config import get_settings
from optimizer.distance_matrix import build_matrix_with_fallback
from optimizer.models import (
    Delivery,
    GeoPoint,
    OptimizationError,
    Vehicle,
    VRPProblem,
)
from optimizer.postprocessor import solution_to_result
from optimizer.preprocessor import needs_decomposition, validate
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


def _build_problem(payload: dict) -> VRPProblem:
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
        )
        for v in payload["vehicles"]
    ]
    constraints = payload.get("constraints", {})
    return VRPProblem(
        depot=depot,
        deliveries=deliveries,
        vehicles=vehicles,
        respect_time_windows=constraints.get("respect_time_windows", True),
        respect_capacity=constraints.get("respect_capacity", True),
    )


async def process_job(message: dict, redis_client: redis.Redis) -> dict:
    """Process one job payload; return the result message the backend persists."""
    started = time.monotonic()
    job_id = message["job_id"]
    company_id = message.get("company_id")

    try:
        problem = _build_problem(message)
        validate(problem)

        if needs_decomposition(problem):
            # TODO: cluster -> solve sub-problems in parallel -> merge (ARCHITECTURE §4.1).
            pass

        points = [problem.depot] + [GeoPoint(d.lat, d.lon) for d in problem.deliveries]
        matrix, used_osrm = await build_matrix_with_fallback(points, redis_client)

        solver = VRPSolver(time_limit_seconds=_time_limit_for(len(problem.deliveries)))
        solution = solver.solve(problem, matrix)
        if not used_osrm:
            solution.is_suboptimal = True  # distances are straight-line approximations

        duration_ms = int((time.monotonic() - started) * 1000)
        return {
            "job_id": job_id,
            "company_id": company_id,
            "status": "completed",
            "error": None,
            "used_osrm": used_osrm,
            **solution_to_result(solution, duration_ms),
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


async def _publish_result(redis_client: redis.Redis, result: dict) -> None:
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
