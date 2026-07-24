"""Dashboard KPI aggregation (F6). Read-only reporting across modules."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.models.delivery import Delivery
from routeopt.models.optimization_job import OptimizationJob
from routeopt.models.route import Route
from routeopt.models.vehicle import Vehicle
from routeopt.modules.dashboard.schemas import DashboardSummary


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def summary(self, company_id: str) -> DashboardSummary:
        cid = uuid.UUID(company_id)
        now = datetime.now(UTC)
        start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)

        # Deliveries grouped by status (non-deleted)
        status_rows = await self.session.execute(
            select(Delivery.status, func.count())
            .where(Delivery.company_id == cid, Delivery.deleted_at.is_(None))
            .group_by(Delivery.status)
        )
        by_status: dict[str, int] = {}
        for status, count in status_rows.all():
            by_status[status] = count

        # Vehicles
        vehicles_total = await self._count(
            Vehicle, Vehicle.company_id == cid, Vehicle.deleted_at.is_(None)
        )
        vehicles_active = await self._count(
            Vehicle,
            Vehicle.company_id == cid,
            Vehicle.deleted_at.is_(None),
            Vehicle.active.is_(True),
        )

        # Routes created today
        today_row = (
            await self.session.execute(
                select(
                    func.count(Route.id),
                    func.coalesce(func.sum(Route.total_distance_m), 0),
                    func.coalesce(func.sum(Route.total_time_s), 0),
                ).where(
                    Route.company_id == cid,
                    Route.deleted_at.is_(None),
                    Route.created_at >= start_today,
                )
            )
        ).one()
        today_routes, today_distance, today_time = today_row

        # Last 7 days
        week_optimizations = await self._count(
            OptimizationJob,
            OptimizationJob.company_id == cid,
            OptimizationJob.status == "completed",
            OptimizationJob.created_at >= week_ago,
        )
        week_distance = await self.session.scalar(
            select(func.coalesce(func.sum(Route.total_distance_m), 0)).where(
                Route.company_id == cid,
                Route.deleted_at.is_(None),
                Route.created_at >= week_ago,
            )
        )

        return DashboardSummary(
            date=now.date().isoformat(),
            deliveries_total=sum(by_status.values()),
            deliveries_by_status=by_status,
            vehicles_active=vehicles_active,
            vehicles_total=vehicles_total,
            today_routes=today_routes,
            today_distance_m=float(today_distance),
            today_time_s=int(today_time),
            week_optimizations=week_optimizations,
            week_distance_m=float(week_distance or 0),
        )

    async def _count(self, model: type[Any], *conditions: ColumnElement[bool]) -> int:
        count = await self.session.scalar(
            select(func.count()).select_from(model).where(*conditions)
        )
        return int(count or 0)
