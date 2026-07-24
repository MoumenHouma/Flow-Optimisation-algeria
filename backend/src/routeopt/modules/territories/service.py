"""Territory management (F15): CRUD + automatic geographic zoning.

``auto_generate`` clusters the company's geocoded deliveries into zones with
K-Means, replaces any existing territories, assigns each delivery to its zone,
and round-robins the active drivers across the zones.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.exceptions import NotFoundError, ValidationError
from routeopt.core.tenancy import validate_driver
from routeopt.models.delivery import Delivery
from routeopt.models.territory import Territory
from routeopt.models.user import User
from routeopt.models.vehicle import Vehicle
from routeopt.modules.territories.clustering import kmeans
from routeopt.modules.territories.schemas import TerritoryIn, TerritoryUpdate

# Distinct zone colours (DESIGN palette family).
_PALETTE = [
    "#2563EB",
    "#10B981",
    "#F59E0B",
    "#EF4444",
    "#8B5CF6",
    "#06B6D4",
    "#EC4899",
    "#84CC16",
]


class TerritoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _counts(self, company_id: str) -> dict[uuid.UUID, int]:
        rows = await self.session.execute(
            select(Delivery.territory_id, func.count())
            .where(
                Delivery.company_id == uuid.UUID(company_id),
                Delivery.deleted_at.is_(None),
                Delivery.territory_id.is_not(None),
            )
            .group_by(Delivery.territory_id)
        )
        return {tid: int(n) for tid, n in rows.all() if tid is not None}

    async def list_territories(self, company_id: str) -> list[tuple[Territory, int]]:
        territories = list(
            await self.session.scalars(
                select(Territory)
                .where(
                    Territory.company_id == uuid.UUID(company_id),
                    Territory.deleted_at.is_(None),
                )
                .order_by(Territory.name)
            )
        )
        counts = await self._counts(company_id)
        return [(t, counts.get(t.id, 0)) for t in territories]

    async def create_territory(self, company_id: str, payload: TerritoryIn) -> Territory:
        territory = Territory(
            company_id=uuid.UUID(company_id),
            name=payload.name,
            color=payload.color,
            driver_user_id=await validate_driver(self.session, company_id, payload.driver_user_id),
        )
        self.session.add(territory)
        await self.session.commit()
        await self.session.refresh(territory)
        return territory

    async def update_territory(
        self, company_id: str, territory_id: str, payload: TerritoryUpdate
    ) -> Territory:
        territory = await self._get_scoped(company_id, territory_id)
        if payload.name is not None:
            territory.name = payload.name
        if payload.color is not None:
            territory.color = payload.color
        # driver_user_id is always assignable (including clearing to null).
        territory.driver_user_id = await validate_driver(
            self.session, company_id, payload.driver_user_id
        )
        await self.session.commit()
        await self.session.refresh(territory)
        return territory

    async def delete_territory(self, company_id: str, territory_id: str) -> None:
        territory = await self._get_scoped(company_id, territory_id)
        await self.session.execute(
            update(Delivery).where(Delivery.territory_id == territory.id).values(territory_id=None)
        )
        territory.deleted_at = datetime.now(UTC)
        await self.session.commit()

    async def auto_generate(
        self, company_id: str, zones: int | None
    ) -> list[tuple[Territory, int]]:
        cid = uuid.UUID(company_id)
        deliveries = list(
            await self.session.scalars(
                select(Delivery).where(
                    Delivery.company_id == cid,
                    Delivery.deleted_at.is_(None),
                    Delivery.lat.is_not(None),
                    Delivery.lon.is_not(None),
                )
            )
        )
        routable = [
            (d, float(d.lat), float(d.lon))
            for d in deliveries
            if d.lat is not None and d.lon is not None
        ]
        if not routable:
            raise ValidationError("No geocoded deliveries to cluster")

        if zones is None:
            zones = await self._active_vehicle_count(company_id) or 1

        points = [(lat, lon) for _, lat, lon in routable]
        assignment, centroids = kmeans(points, zones)
        k = len(centroids)

        # Replace existing zones: detach deliveries, soft-delete old territories.
        await self.session.execute(
            update(Delivery)
            .where(Delivery.company_id == cid, Delivery.territory_id.is_not(None))
            .values(territory_id=None)
        )
        now = datetime.now(UTC)
        for old in await self.session.scalars(
            select(Territory).where(Territory.company_id == cid, Territory.deleted_at.is_(None))
        ):
            old.deleted_at = now

        drivers = await self._active_drivers(company_id)
        territories: list[Territory] = []
        for i in range(k):
            t = Territory(
                company_id=cid,
                name=f"Zone {i + 1}",
                color=_PALETTE[i % len(_PALETTE)],
                centroid_lat=centroids[i][0],
                centroid_lon=centroids[i][1],
                driver_user_id=drivers[i % len(drivers)] if drivers else None,
            )
            self.session.add(t)
            territories.append(t)
        await self.session.flush()

        counts = [0] * k
        for (d, _lat, _lon), cluster in zip(routable, assignment, strict=True):
            d.territory_id = territories[cluster].id
            counts[cluster] += 1

        await self.session.commit()
        for t in territories:
            await self.session.refresh(t)
        return list(zip(territories, counts, strict=True))

    async def _active_drivers(self, company_id: str) -> list[uuid.UUID]:
        rows = await self.session.scalars(
            select(User.id)
            .where(
                User.company_id == uuid.UUID(company_id),
                User.role == "driver",
                User.active.is_(True),
                User.deleted_at.is_(None),
            )
            .order_by(User.created_at)
        )
        return list(rows)

    async def _active_vehicle_count(self, company_id: str) -> int:
        count = await self.session.scalar(
            select(func.count())
            .select_from(Vehicle)
            .where(
                Vehicle.company_id == uuid.UUID(company_id),
                Vehicle.deleted_at.is_(None),
                Vehicle.active.is_(True),
            )
        )
        return int(count or 0)

    async def _get_scoped(self, company_id: str, territory_id: str) -> Territory:
        territory = await self.session.get(Territory, uuid.UUID(territory_id))
        if (
            territory is None
            or str(territory.company_id) != company_id
            or territory.deleted_at is not None
        ):
            raise NotFoundError("Territory not found")
        return territory
