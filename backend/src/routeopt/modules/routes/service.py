"""Route optimization orchestration (docs/ARCHITECTURE.md §3.1).

Optimization is asynchronous: submit_job builds the full problem from the DB,
creates an OptimizationJob, and enqueues it for the worker. The worker writes its
result to ``opt:result:{job_id}``; get_job persists that result lazily on the
first poll after completion (idempotent — only pending/running jobs are persisted).

Worker/backend share only the JSON message contract, not code — the result shape
mirrors optimizer.postprocessor.solution_to_result.
"""

import json
import uuid
from datetime import UTC, datetime, time
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.config import get_settings
from routeopt.core.exceptions import NotFoundError, ValidationError
from routeopt.models.delivery import Delivery
from routeopt.models.optimization_job import OptimizationJob
from routeopt.models.route import Route, RouteStop
from routeopt.models.vehicle import Vehicle
from routeopt.modules.routes.schemas import OptimizeRequest, ReoptimizeRequest
from routeopt.redis_client import redis_client

settings = get_settings()

RESULT_KEY = "opt:result:{job_id}"

# A stop is "done" and stays fixed at the front when re-optimizing a live route.
_DONE_STATUSES = ("delivered", "failed", "cancelled")


def _req_float(value: float | None) -> float:
    """Narrow a nullable numeric known to be non-null (query-filtered)."""
    assert value is not None
    return float(value)


def _time_window_seconds(delivery: Delivery) -> list[int] | None:
    if delivery.time_window_start is None or delivery.time_window_end is None:
        return None

    def to_s(t: time) -> int:
        return t.hour * 3600 + t.minute * 60 + t.second

    return [to_s(delivery.time_window_start), to_s(delivery.time_window_end)]


class RoutesService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def submit_job(
        self, company_id: str, user_id: str, payload: OptimizeRequest
    ) -> tuple[str, int]:
        """Create + enqueue an optimization job. Returns (job_id, delivery_count)."""
        deliveries = await self._resolve_deliveries(company_id, payload.delivery_ids)
        vehicles = await self._resolve_vehicles(company_id, payload.vehicle_ids)
        if not deliveries:
            raise ValidationError("No routable deliveries (need geocoded, unassigned stops)")
        if not vehicles:
            raise ValidationError("No active vehicles available")

        # MVP single-depot: use the request depot, else the first vehicle's depot.
        if payload.depot is not None:
            depot = {"lat": payload.depot.lat, "lon": payload.depot.lon}
        else:
            depot = {"lat": float(vehicles[0].depot_lat), "lon": float(vehicles[0].depot_lon)}

        job = OptimizationJob(
            company_id=uuid.UUID(company_id),
            requested_by_user_id=uuid.UUID(user_id),
            status="pending",
            delivery_count=len(deliveries),
            vehicle_count=len(vehicles),
            created_at=datetime.now(UTC),
        )
        self.session.add(job)
        await self.session.flush()

        message = {
            "job_id": str(job.id),
            "company_id": company_id,
            "depot": depot,
            "constraints": payload.constraints.model_dump(),
            "deliveries": [
                {
                    "id": str(d.id),
                    "lat": _req_float(d.lat),
                    "lon": _req_float(d.lon),
                    "demand": float(d.weight),
                    "service_time": d.service_time,
                    "priority": d.priority,
                    "time_window": _time_window_seconds(d),
                }
                for d in deliveries
            ],
            "vehicles": [
                {
                    "id": str(v.id),
                    "capacity": float(v.capacity_weight),
                    "depot": {"lat": float(v.depot_lat), "lon": float(v.depot_lon)},
                }
                for v in vehicles
            ],
        }
        await redis_client.rpush(settings.optimize_queue, json.dumps(message))
        await self.session.commit()
        return str(job.id), len(deliveries)

    async def submit_reoptimize_job(
        self, company_id: str, user_id: str, route_id: str, payload: ReoptimizeRequest
    ) -> tuple[str, int]:
        """Re-plan a live route's *remaining* stops from the driver's position (F9)."""
        route = await self.get_route(company_id, route_id)
        if route.vehicle_id is None:
            raise ValidationError("Route has no vehicle to re-optimize")
        vehicle = await self.session.get(Vehicle, route.vehicle_id)
        if vehicle is None:
            raise ValidationError("Route vehicle not found")

        remaining = await self._remaining_deliveries(route.id)
        if not remaining:
            raise ValidationError("No remaining stops to re-optimize")

        # Start the re-planned leg where the driver is now, else the depot.
        if payload.current_lat is not None and payload.current_lon is not None:
            depot = {"lat": payload.current_lat, "lon": payload.current_lon}
        else:
            depot = {"lat": float(vehicle.depot_lat), "lon": float(vehicle.depot_lon)}

        job = OptimizationJob(
            company_id=uuid.UUID(company_id),
            requested_by_user_id=uuid.UUID(user_id),
            reoptimize_route_id=route.id,
            trigger="reoptimize",
            status="pending",
            delivery_count=len(remaining),
            vehicle_count=1,
            created_at=datetime.now(UTC),
        )
        self.session.add(job)
        await self.session.flush()

        message = {
            "job_id": str(job.id),
            "company_id": company_id,
            "depot": depot,
            "constraints": payload.constraints.model_dump(),
            "deliveries": [
                {
                    "id": str(d.id),
                    "lat": _req_float(d.lat),
                    "lon": _req_float(d.lon),
                    "demand": float(d.weight),
                    "service_time": d.service_time,
                    "priority": d.priority,
                    "time_window": _time_window_seconds(d),
                }
                for d in remaining
            ],
            "vehicles": [
                {
                    "id": str(vehicle.id),
                    "capacity": float(vehicle.capacity_weight),
                    "depot": depot,
                }
            ],
        }
        await redis_client.rpush(settings.optimize_queue, json.dumps(message))
        await self.session.commit()
        return str(job.id), len(remaining)

    async def get_job(self, company_id: str, job_id: str) -> OptimizationJob:
        job = await self._get_job_scoped(company_id, job_id)
        if job.status in ("pending", "running"):
            raw = await redis_client.get(RESULT_KEY.format(job_id=job_id))
            if raw:
                await self.persist_result(json.loads(raw))
                await self.session.refresh(job)
        return job

    async def route_ids_for_job(self, job_id: str) -> list[str]:
        result = await self.session.scalars(
            select(Route.id).where(Route.optimization_job_id == uuid.UUID(job_id))
        )
        return [str(r) for r in result]

    async def get_route(self, company_id: str, route_id: str) -> Route:
        route = await self.session.get(Route, uuid.UUID(route_id))
        if route is None or str(route.company_id) != company_id or route.deleted_at is not None:
            raise NotFoundError("Route not found")
        await self.session.refresh(route, attribute_names=["stops"])
        return route

    async def get_route_detail(
        self, company_id: str, route_id: str
    ) -> tuple[Route, dict[uuid.UUID, Delivery], dict[str, float] | None]:
        """Return (route, deliveries_by_id, depot) — enough to draw the route on a map."""
        route = await self.get_route(company_id, route_id)

        ids = [s.delivery_id for s in route.stops]
        deliveries_by_id: dict[uuid.UUID, Delivery] = {}
        if ids:
            rows = await self.session.scalars(select(Delivery).where(Delivery.id.in_(ids)))
            deliveries_by_id = {d.id: d for d in rows}

        depot: dict[str, float] | None = None
        if route.vehicle_id is not None:
            vehicle = await self.session.get(Vehicle, route.vehicle_id)
            if vehicle is not None:
                depot = {"lat": float(vehicle.depot_lat), "lon": float(vehicle.depot_lon)}
        return route, deliveries_by_id, depot

    async def persist_result(self, message: dict[str, Any]) -> None:
        """Persist a worker result message (idempotent: pending/running only)."""
        job = await self.session.get(OptimizationJob, uuid.UUID(message["job_id"]))
        if job is None or job.status not in ("pending", "running"):
            return

        now = datetime.now(UTC)
        if message.get("status") == "failed":
            job.status = "failed"
            job.error_message = message.get("error")
            job.duration_ms = message.get("duration_ms")
            job.completed_at = now
            await self.session.commit()
            return

        if job.reoptimize_route_id is not None:
            await self._persist_reoptimize(job, message, now)
            return

        for route_msg in message.get("routes", []):
            route = Route(
                company_id=job.company_id,
                vehicle_id=(
                    uuid.UUID(route_msg["vehicle_id"]) if route_msg.get("vehicle_id") else None
                ),
                optimization_job_id=job.id,
                total_distance_m=route_msg.get("total_distance_m"),
                total_time_s=route_msg.get("total_time_s"),
                geometry=route_msg.get("geometry"),
                status="planned",
                optimized_at=now,
            )
            self.session.add(route)
            await self.session.flush()
            for stop in route_msg.get("stops", []):
                self.session.add(
                    RouteStop(
                        route_id=route.id,
                        delivery_id=uuid.UUID(stop["delivery_id"]),
                        sequence=stop["sequence"],
                    )
                )
                delivery = await self.session.get(Delivery, uuid.UUID(stop["delivery_id"]))
                if delivery is not None:
                    delivery.route_id = route.id
                    delivery.status = "assigned"

        job.status = "completed"
        job.solver_strategy = message.get("strategy")
        job.duration_ms = message.get("duration_ms")
        job.result = {
            "total_distance_m": message.get("total_distance_m"),
            "total_time_s": message.get("total_time_s"),
            "objective_value": message.get("objective_value"),
            "used_osrm": message.get("used_osrm"),
            "is_suboptimal": message.get("is_suboptimal"),
        }
        job.completed_at = now
        await self.session.commit()

    async def _persist_reoptimize(
        self, job: OptimizationJob, message: dict[str, Any], now: datetime
    ) -> None:
        """Re-plan an existing route in place: keep done stops, re-sequence the rest."""
        assert job.reoptimize_route_id is not None
        route = await self.session.get(Route, job.reoptimize_route_id)
        if route is None or route.deleted_at is not None:
            job.status = "completed"
            job.completed_at = now
            await self.session.commit()
            return

        await self.session.refresh(route, attribute_names=["stops"])
        ids = [s.delivery_id for s in route.stops]
        deliveries = {
            d.id: d
            for d in await self.session.scalars(select(Delivery).where(Delivery.id.in_(ids)))
        }
        # Done stops stay fixed at the front, preserving their visiting order.
        done_ids = [
            s.delivery_id
            for s in sorted(route.stops, key=lambda x: x.sequence)
            if (d := deliveries.get(s.delivery_id)) is not None and d.status in _DONE_STATUSES
        ]
        # The worker returns the new order for the remaining deliveries.
        routes_msg = message.get("routes", [])
        new_order = (
            [s["delivery_id"] for s in sorted(routes_msg[0]["stops"], key=lambda s: s["sequence"])]
            if routes_msg
            else []
        )

        # Rebuild route_stops = done (unchanged order) + remaining (new order).
        await self.session.execute(delete(RouteStop).where(RouteStop.route_id == route.id))
        await self.session.flush()
        for seq, delivery_id in enumerate([*done_ids, *new_order]):
            self.session.add(
                RouteStop(route_id=route.id, delivery_id=uuid.UUID(str(delivery_id)), sequence=seq)
            )

        if routes_msg:
            route.total_distance_m = routes_msg[0].get("total_distance_m")
            route.total_time_s = routes_msg[0].get("total_time_s")
            route.geometry = routes_msg[0].get("geometry")
        route.optimization_job_id = job.id
        route.optimized_at = now

        job.status = "completed"
        job.solver_strategy = message.get("strategy")
        job.duration_ms = message.get("duration_ms")
        job.result = {
            "total_distance_m": message.get("total_distance_m"),
            "total_time_s": message.get("total_time_s"),
            "objective_value": message.get("objective_value"),
            "used_osrm": message.get("used_osrm"),
            "is_suboptimal": message.get("is_suboptimal"),
        }
        job.completed_at = now
        await self.session.commit()

    @staticmethod
    def estimate_duration_ms(num_deliveries: int) -> int:
        return max(1000, num_deliveries * 100)

    # ── helpers ──────────────────────────────────────────────────────────
    async def _resolve_deliveries(self, company_id: str, ids: list[str]) -> list[Delivery]:
        stmt = select(Delivery).where(
            Delivery.company_id == uuid.UUID(company_id),
            Delivery.deleted_at.is_(None),
            Delivery.route_id.is_(None),
            Delivery.lat.is_not(None),
            Delivery.lon.is_not(None),
        )
        if ids:
            stmt = stmt.where(Delivery.id.in_([uuid.UUID(i) for i in ids]))
        return list(await self.session.scalars(stmt))

    async def _remaining_deliveries(self, route_id: uuid.UUID) -> list[Delivery]:
        """Geocoded, not-yet-done stops on a route — the re-optimizable set (F9)."""
        stmt = select(Delivery).where(
            Delivery.route_id == route_id,
            Delivery.deleted_at.is_(None),
            Delivery.status.not_in(_DONE_STATUSES),
            Delivery.lat.is_not(None),
            Delivery.lon.is_not(None),
        )
        return list(await self.session.scalars(stmt))

    async def _resolve_vehicles(self, company_id: str, ids: list[str]) -> list[Vehicle]:
        stmt = select(Vehicle).where(
            Vehicle.company_id == uuid.UUID(company_id),
            Vehicle.deleted_at.is_(None),
            Vehicle.active.is_(True),
        )
        if ids:
            stmt = stmt.where(Vehicle.id.in_([uuid.UUID(i) for i in ids]))
        return list(await self.session.scalars(stmt))

    async def _get_job_scoped(self, company_id: str, job_id: str) -> OptimizationJob:
        job = await self.session.get(OptimizationJob, uuid.UUID(job_id))
        if job is None or str(job.company_id) != company_id:
            raise NotFoundError("Job not found")
        return job
