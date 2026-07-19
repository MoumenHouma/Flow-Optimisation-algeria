"""End-to-end worker test: job payload -> solved result message.

No OSRM available, so the haversine fallback is exercised (used_osrm=False).
"""

import fakeredis.aioredis
import pytest

from optimizer.worker import process_job

# Two deliveries near Alger centre + a depot, one vehicle with enough capacity.
JOB = {
    "job_id": "job-1",
    "company_id": "co-1",
    "depot": {"lat": 36.7538, "lon": 3.0588},
    "constraints": {"respect_time_windows": False, "respect_capacity": True},
    "deliveries": [
        {"id": "d1", "lat": 36.75, "lon": 3.06, "demand": 2},
        {"id": "d2", "lat": 36.76, "lon": 3.07, "demand": 3},
    ],
    "vehicles": [{"id": "v1", "capacity": 100, "depot": {"lat": 36.7538, "lon": 3.0588}}],
}


@pytest.fixture
def redis_client():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


async def test_process_job_solves_with_haversine_fallback(redis_client) -> None:
    result = await process_job(JOB, redis_client)

    assert result["job_id"] == "job-1"
    assert result["status"] == "completed"
    assert result["used_osrm"] is False
    assert result["is_suboptimal"] is True  # straight-line approximation
    assert result["total_distance_m"] > 0

    served = {s["delivery_id"] for r in result["routes"] for s in r["stops"]}
    assert served == {"d1", "d2"}


async def test_process_job_reports_infeasible(redis_client) -> None:
    infeasible = {
        **JOB,
        "vehicles": [{"id": "v1", "capacity": 1, "depot": JOB["depot"]}],  # < total demand 5
    }
    result = await process_job(infeasible, redis_client)
    assert result["status"] == "failed"
    assert "infeasible" in result["error"]
