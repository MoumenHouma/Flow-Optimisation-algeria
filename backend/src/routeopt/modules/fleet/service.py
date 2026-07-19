"""Fleet logic: vehicle CRUD with plan-quota enforcement (SCHEMA §3.1)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.exceptions import ConflictError, NotFoundError
from routeopt.core.security import hash_password
from routeopt.models.company import Company
from routeopt.models.user import User
from routeopt.models.vehicle import Vehicle
from routeopt.modules.fleet.schemas import DriverIn, FleetSummary, VehicleIn


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

    async def update_vehicle(self, company_id: str, vehicle_id: str, payload: VehicleIn) -> Vehicle:
        vehicle = await self._get_scoped(company_id, vehicle_id)
        vehicle.name = payload.name
        vehicle.vehicle_type = payload.vehicle_type
        vehicle.license_plate = payload.license_plate
        vehicle.capacity_weight = payload.capacity_weight
        vehicle.capacity_volume = payload.capacity_volume
        vehicle.depot_lat = payload.depot.lat
        vehicle.depot_lon = payload.depot.lon
        vehicle.depot_address = payload.depot_address
        vehicle.driver_user_id = (
            uuid.UUID(payload.driver_user_id) if payload.driver_user_id else None
        )
        await self.session.commit()
        await self.session.refresh(vehicle)
        return vehicle

    async def delete_vehicle(self, company_id: str, vehicle_id: str) -> None:
        vehicle = await self._get_scoped(company_id, vehicle_id)
        vehicle.deleted_at = datetime.now(UTC)  # soft delete (RULES §2.4)
        vehicle.active = False
        await self.session.commit()

    async def create_driver(self, company_id: str, payload: DriverIn) -> User:
        """Create a role=driver login so a manager can onboard + assign drivers (F8)."""
        driver = User(
            company_id=uuid.UUID(company_id),
            email=payload.email.lower(),
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            phone=payload.phone,
            role="driver",
        )
        self.session.add(driver)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Email already registered") from exc
        await self.session.refresh(driver)
        return driver

    async def summary(self, company_id: str) -> FleetSummary:
        company = await self.session.get(Company, uuid.UUID(company_id))
        if company is None:
            raise NotFoundError("Company not found")
        count = await self._active_count(company_id)
        return FleetSummary(
            plan=company.plan,
            vehicle_count=count,
            max_vehicles=company.max_vehicles,
        )

    async def _get_scoped(self, company_id: str, vehicle_id: str) -> Vehicle:
        vehicle = await self.session.get(Vehicle, uuid.UUID(vehicle_id))
        if (
            vehicle is None
            or str(vehicle.company_id) != company_id
            or vehicle.deleted_at is not None
        ):
            raise NotFoundError("Vehicle not found")
        return vehicle

    async def _active_count(self, company_id: str) -> int:
        count = await self.session.scalar(
            select(func.count())
            .select_from(Vehicle)
            .where(Vehicle.company_id == uuid.UUID(company_id), Vehicle.deleted_at.is_(None))
        )
        return count or 0

    async def _enforce_quota(self, company_id: str) -> None:
        company = await self.session.get(Company, uuid.UUID(company_id))
        if company is None:
            raise NotFoundError("Company not found")
        if company.max_vehicles is None:  # unlimited (Enterprise)
            return
        if await self._active_count(company_id) >= company.max_vehicles:
            raise ConflictError(
                f"Vehicle quota reached for plan '{company.plan}' ({company.max_vehicles})"
            )
