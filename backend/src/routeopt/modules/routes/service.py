"""Route optimization orchestration.

Optimization is asynchronous (docs/ARCHITECTURE.md §3.1): the API creates an
OptimizationJob row, pushes the job id onto the Redis queue consumed by the
optimization worker, and returns immediately. Clients poll GET /routes jobs or
subscribe via SSE.
"""

import json
import uuid

from routeopt.config import get_settings
from routeopt.redis_client import redis_client

settings = get_settings()


class RoutesService:
    async def submit_job(self, company_id: str, payload: dict) -> str:
        """Enqueue an optimization job, return its id."""
        job_id = str(uuid.uuid4())
        message = {"job_id": job_id, "company_id": company_id, "payload": payload}
        # TODO: persist OptimizationJob(status='pending') before enqueue.
        await redis_client.rpush(settings.optimize_queue, json.dumps(message))
        return job_id

    @staticmethod
    def estimate_duration_ms(num_deliveries: int) -> int:
        """Rough ETA shown to the user (docs/RULES.md §7.1 budgets)."""
        # ~100ms/stop as a first-order estimate; refined from historical jobs later.
        return max(1000, num_deliveries * 100)

    async def get_route(self, company_id: str, route_id: str) -> object:
        raise NotImplementedError("fetch route + stops scoped to company_id")

    async def export(self, company_id: str, route_id: str, fmt: str) -> bytes:
        # TODO: PDF / Excel / GPX export (F5).
        raise NotImplementedError("export route as pdf/excel/gpx")

    async def reoptimize(self, company_id: str, route_id: str) -> str:
        """Dynamic re-optimization with warm-start (F9)."""
        raise NotImplementedError("enqueue reoptimize job with current state")
