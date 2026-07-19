"""Queue consumer: pops optimization jobs from Redis and runs the solver.

Flow (docs/ARCHITECTURE.md §3.1): BLPOP queue:optimize -> build problem ->
distance matrix (OSRM+cache) -> solve -> persist result -> notify subscribers.
"""

from __future__ import annotations

import asyncio
import json
import time

import redis.asyncio as redis

from optimizer.config import get_settings
from optimizer.distance_matrix import build_distance_matrix
from optimizer.models import GeoPoint, OptimizationError, VRPProblem
from optimizer.postprocessor import solution_to_result
from optimizer.preprocessor import needs_decomposition, validate
from optimizer.solver import VRPSolver

settings = get_settings()


def _time_limit_for(num_deliveries: int) -> int:
    if num_deliveries < 50:
        return settings.time_limit_small_s
    if num_deliveries < 200:
        return settings.time_limit_medium_s
    return settings.time_limit_large_s


async def process_job(message: dict, redis_client: redis.Redis) -> dict:
    """Process one job payload, returning the serialized result."""
    started = time.monotonic()
    problem = _build_problem(message["payload"])
    validate(problem)

    if needs_decomposition(problem):
        # TODO: cluster -> solve sub-problems in parallel -> merge (ARCHITECTURE §4.1).
        pass

    points = [problem.depot] + [GeoPoint(d.lat, d.lon) for d in problem.deliveries]
    matrix = await build_distance_matrix(points, redis_client)

    solver = VRPSolver(time_limit_seconds=_time_limit_for(len(problem.deliveries)))
    solution = solver.solve(problem, matrix)

    duration_ms = int((time.monotonic() - started) * 1000)
    return solution_to_result(solution, duration_ms)


def _build_problem(payload: dict) -> VRPProblem:
    # TODO: hydrate deliveries/vehicles from payload ids via the backend/DB.
    raise NotImplementedError("hydrate VRPProblem from job payload")


async def run() -> None:
    redis_client: redis.Redis = redis.from_url(settings.redis_url, decode_responses=True)
    print(f"[optimizer] listening on {settings.optimize_queue}")  # noqa: T201
    while True:
        item = await redis_client.blpop([settings.optimize_queue], timeout=5)
        if item is None:
            continue
        _, raw = item
        message = json.loads(raw)
        try:
            result = await process_job(message, redis_client)
            # TODO: persist result to optimization_jobs + publish SSE notification.
            print(f"[optimizer] job {message['job_id']} done: {result['strategy']}")  # noqa: T201
        except OptimizationError as exc:
            print(f"[optimizer] job {message['job_id']} failed: {exc}")  # noqa: T201
        except NotImplementedError as exc:  # scaffold guard
            print(f"[optimizer] job {message['job_id']} not wired: {exc}")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(run())
