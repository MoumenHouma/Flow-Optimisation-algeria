"""Fleet logic: vehicle CRUD with plan-quota enforcement (SCHEMA §3.1)."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.exceptions import ConflictError, NotFoundError
from routeopt.models.company import Company
from routeopt.models.vehicle import Vehicle
from routeopt.modules.fleet.schemas import VehicleIn


class FleetService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_vehicles(self, company_id: str) -> list[Vehicle]:
        result = await self.session.scalars(
            select(Vehicle).where(
                Vehicle.company_id == uuid.UUID(company_id),
                Vehicle.deleted_at.is_(None),
            )
        )
        return list(result)

    async def add_vehicle(self, company_id: str, payload: VehicleIn) -> Vehicle:
        await self._enforce_quota(company_id)
        vehicle = Vehicle(
            company_id=uuid.UUID(company_id),
            name=payload.name,
            vehicle_type=payload.vehicle_type,
            license_plate=payload.license_plate,
            capacity_weight=payload.capacity_weight,
            capacity_volume=payload.capacity_volume,
            depot_lat=payload.depot.lat,
            depot_lon=payload.depot.lon,
            depot_address=payload.depot_address,
            driver_user_id=uuid.UUID(payload.driver_user_id) if payload.driver_user_id else None,
        )
        self.session.add(vehicle)
        await self.session.commit()
        await self.session.refresh(vehicle)
        return vehicle

    async def _enforce_quota(self, company_id: str) -> None:
        company = await self.session.get(Company, uuid.UUID(company_id))
        if company is None:
            raise NotFoundError("Company not found")
        if company.max_vehicles is None:  # unlimited (Enterprise)
            return
        count = await self.session.scalar(
            select(func.count())
            .select_from(Vehicle)
            .where(Vehicle.company_id == uuid.UUID(company_id), Vehicle.deleted_at.is_(None))
        )
        if count is not None and count >= company.max_vehicles:
            raise ConflictError(
                f"Vehicle quota reached for plan '{company.plan}' ({company.max_vehicles})"
            )
