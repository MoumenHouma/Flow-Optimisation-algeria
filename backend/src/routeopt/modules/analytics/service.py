"""Analytics aggregation (F11): trends + delivery performance.

Grounded in the data the platform captures as it runs: the append-only
``delivery_status_history`` (delivered/failed events, reasons, the acting driver)
and ``routes`` (distance). Read-only; scoped to the caller's company.
``delivery_status_history`` has no company_id, so it is joined to ``deliveries``.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.models.delivery import Delivery
from routeopt.models.delivery_status_history import DeliveryStatusHistory
from routeopt.models.route import Route
from routeopt.models.user import User
from routeopt.modules.analytics.schemas import (
    DriverStat,
    FailureReason,
    PerformanceOut,
    TrendPoint,
    TrendsOut,
)

_MAX_DAYS = 365


def _clamp_days(days: int) -> int:
    return max(1, min(days, _MAX_DAYS))


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def trends(self, company_id: str, days: int) -> TrendsOut:
        days = _clamp_days(days)
        cid = uuid.UUID(company_id)
        now = datetime.now(UTC)
        start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)

        day = func.date_trunc("day", DeliveryStatusHistory.created_at)
        status_rows = await self.session.execute(
            select(day, DeliveryStatusHistory.to_status, func.count())
            .join(Delivery, Delivery.id == DeliveryStatusHistory.delivery_id)
            .where(
                Delivery.company_id == cid,
                DeliveryStatusHistory.created_at >= start,
                DeliveryStatusHistory.to_status.in_(("delivered", "failed")),
            )
            .group_by(day, DeliveryStatusHistory.to_status)
        )
        completed: dict[str, int] = {}
        failed: dict[str, int] = {}
        for bucket, to_status, count in status_rows.all():
            key = bucket.date().isoformat()
            (completed if to_status == "delivered" else failed)[key] = int(count)

        rday = func.date_trunc("day", Route.created_at)
        route_rows = await self.session.execute(
            select(rday, func.count(Route.id), func.coalesce(func.sum(Route.total_distance_m), 0))
            .where(
                Route.company_id == cid,
                Route.deleted_at.is_(None),
                Route.created_at >= start,
            )
            .group_by(rday)
        )
        route_counts: dict[str, int] = {}
        route_distance: dict[str, float] = {}
        for bucket, count, distance in route_rows.all():
            key = bucket.date().isoformat()
            route_counts[key] = int(count)
            route_distance[key] = float(distance)

        points = [
            TrendPoint(
                date=key,
                deliveries_completed=completed.get(key, 0),
                deliveries_failed=failed.get(key, 0),
                routes=route_counts.get(key, 0),
                distance_m=route_distance.get(key, 0.0),
            )
            for key in ((start + timedelta(days=i)).date().isoformat() for i in range(days))
        ]
        return TrendsOut(days=days, points=points)

    async def performance(self, company_id: str, days: int) -> PerformanceOut:
        days = _clamp_days(days)
        cid = uuid.UUID(company_id)
        since = datetime.now(UTC) - timedelta(days=days)

        # Delivered / failed totals over the window.
        status_rows = await self.session.execute(
            select(DeliveryStatusHistory.to_status, func.count())
            .join(Delivery, Delivery.id == DeliveryStatusHistory.delivery_id)
            .where(
                Delivery.company_id == cid,
                DeliveryStatusHistory.created_at >= since,
                DeliveryStatusHistory.to_status.in_(("delivered", "failed")),
            )
            .group_by(DeliveryStatusHistory.to_status)
        )
        totals = {to_status: int(count) for to_status, count in status_rows.all()}
        delivered = totals.get("delivered", 0)
        failed = totals.get("failed", 0)
        done = delivered + failed
        success_rate = round(delivered / done, 4) if done else 0.0

        # Failure reasons breakdown (group on the raw column; label NULLs after).
        reason_rows = await self.session.execute(
            select(DeliveryStatusHistory.reason, func.count())
            .join(Delivery, Delivery.id == DeliveryStatusHistory.delivery_id)
            .where(
                Delivery.company_id == cid,
                DeliveryStatusHistory.created_at >= since,
                DeliveryStatusHistory.to_status == "failed",
            )
            .group_by(DeliveryStatusHistory.reason)
            .order_by(func.count().desc())
        )
        failure_reasons = [
            FailureReason(reason=reason or "unspecified", count=int(count))
            for reason, count in reason_rows.all()
        ]

        # Per-driver delivered/failed leaderboard.
        driver_rows = await self.session.execute(
            select(
                DeliveryStatusHistory.changed_by_user_id,
                User.full_name,
                DeliveryStatusHistory.to_status,
                func.count(),
            )
            .join(Delivery, Delivery.id == DeliveryStatusHistory.delivery_id)
            .join(User, User.id == DeliveryStatusHistory.changed_by_user_id)
            .where(
                Delivery.company_id == cid,
                DeliveryStatusHistory.created_at >= since,
                DeliveryStatusHistory.to_status.in_(("delivered", "failed")),
            )
            .group_by(
                DeliveryStatusHistory.changed_by_user_id,
                User.full_name,
                DeliveryStatusHistory.to_status,
            )
        )
        drivers: dict[str, DriverStat] = {}
        for driver_id, name, to_status, count in driver_rows.all():
            key = str(driver_id)
            stat = drivers.setdefault(
                key, DriverStat(driver_id=key, driver_name=name, delivered=0, failed=0)
            )
            if to_status == "delivered":
                stat.delivered = int(count)
            else:
                stat.failed = int(count)
        driver_list = sorted(drivers.values(), key=lambda d: d.delivered, reverse=True)

        # Distance over the window.
        route_row = (
            await self.session.execute(
                select(
                    func.count(Route.id),
                    func.coalesce(func.sum(Route.total_distance_m), 0),
                ).where(
                    Route.company_id == cid,
                    Route.deleted_at.is_(None),
                    Route.created_at >= since,
                )
            )
        ).one()
        routes = int(route_row[0])
        total_distance = float(route_row[1])

        return PerformanceOut(
            range_days=days,
            delivered=delivered,
            failed=failed,
            success_rate=success_rate,
            total_distance_m=total_distance,
            routes=routes,
            avg_distance_per_route_m=round(total_distance / routes, 2) if routes else 0.0,
            failure_reasons=failure_reasons,
            drivers=driver_list,
        )
