"""Fleet logic: vehicle CRUD with plan-quota enforcement (SCHEMA §3.1)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.exceptions import ConflictError, NotFoundError, ValidationError
from routeopt.core.security import hash_password
from routeopt.core.tenancy import validate_driver
from routeopt.models.company import Company
from routeopt.models.depot import Depot
from routeopt.models.user import User
from routeopt.models.vehicle import Vehicle
from routeopt.modules.fleet.schemas import DepotIn, DriverIn, FleetSummary, VehicleIn


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
        depot_id, lat, lon, address = await self._resolve_depot(company_id, payload)
        vehicle = Vehicle(
            company_id=uuid.UUID(company_id),
            name=payload.name,
            vehicle_type=payload.vehicle_type,
            license_plate=payload.license_plate,
            capacity_weight=payload.capacity_weight,
            capacity_volume=payload.capacity_volume,
            fuel_range_km=payload.fuel_range_km,
            fuel_type=payload.fuel_type,
            depot_id=depot_id,
            depot_lat=lat,
            depot_lon=lon,
            depot_address=address,
            driver_user_id=await validate_driver(self.session, company_id, payload.driver_user_id),
        )
        self.session.add(vehicle)
        await self.session.commit()
        await self.session.refresh(vehicle)
        return vehicle

    async def update_vehicle(self, company_id: str, vehicle_id: str, payload: VehicleIn) -> Vehicle:
        vehicle = await self._get_scoped(company_id, vehicle_id)
        depot_id, lat, lon, address = await self._resolve_depot(company_id, payload)
        vehicle.name = payload.name
        vehicle.vehicle_type = payload.vehicle_type
        vehicle.license_plate = payload.license_plate
        vehicle.capacity_weight = payload.capacity_weight
        vehicle.capacity_volume = payload.capacity_volume
        vehicle.fuel_range_km = payload.fuel_range_km
        vehicle.fuel_type = payload.fuel_type
        vehicle.depot_id = depot_id
        vehicle.depot_lat = lat
        vehicle.depot_lon = lon
        vehicle.depot_address = address
        vehicle.driver_user_id = await validate_driver(
            self.session, company_id, payload.driver_user_id
        )
        await self.session.commit()
        await self.session.refresh(vehicle)
        return vehicle

    async def _resolve_depot(
        self, company_id: str, payload: VehicleIn
    ) -> tuple[uuid.UUID | None, float, float, str]:
        """A vehicle's departure point: from a depot (F12) or inline coordinates."""
        if payload.depot_id:
            depot = await self.session.get(Depot, uuid.UUID(payload.depot_id))
            if depot is None or str(depot.company_id) != company_id or depot.deleted_at is not None:
                raise NotFoundError("Depot not found")
            return depot.id, float(depot.lat), float(depot.lon), depot.address
        if payload.depot is None or payload.depot_address is None:
            raise ValidationError("Provide a depot_id or an inline depot with address")
        return None, payload.depot.lat, payload.depot.lon, payload.depot_address

    # ── depots (F12 multi-dépôt) ─────────────────────────────────────────
    async def list_depots(self, company_id: str) -> list[Depot]:
        result = await self.session.scalars(
            select(Depot).where(
                Depot.company_id == uuid.UUID(company_id),
                Depot.deleted_at.is_(None),
            )
        )
        return list(result)

    async def add_depot(self, company_id: str, payload: DepotIn) -> Depot:
        depot = Depot(
            company_id=uuid.UUID(company_id),
            name=payload.name,
            lat=payload.location.lat,
            lon=payload.location.lon,
            address=payload.address,
            active=payload.active,
        )
        self.session.add(depot)
        await self.session.commit()
        await self.session.refresh(depot)
        return depot

    async def update_depot(self, company_id: str, depot_id: str, payload: DepotIn) -> Depot:
        depot = await self._get_depot_scoped(company_id, depot_id)
        depot.name = payload.name
        depot.lat = payload.location.lat
        depot.lon = payload.location.lon
        depot.address = payload.address
        depot.active = payload.active
        await self.session.commit()
        await self.session.refresh(depot)
        return depot

    async def delete_depot(self, company_id: str, depot_id: str) -> None:
        depot = await self._get_depot_scoped(company_id, depot_id)
        depot.deleted_at = datetime.now(UTC)  # soft delete; vehicles keep resolved coords
        await self.session.commit()

    async def _get_depot_scoped(self, company_id: str, depot_id: str) -> Depot:
        depot = await self.session.get(Depot, uuid.UUID(depot_id))
        if depot is None or str(depot.company_id) != company_id or depot.deleted_at is not None:
            raise NotFoundError("Depot not found")
        return depot

    async def delete_vehicle(self, company_id: str, vehicle_id: str) -> None:
        vehicle = await self._get_scoped(company_id, vehicle_id)
        vehicle.deleted_at = datetime.now(UTC)  # soft delete (RULES §2.4)
        vehicle.active = False
        await self.session.commit()

    async def list_drivers(self, company_id: str) -> list[User]:
        result = await self.session.scalars(
            select(User).where(
                User.company_id == uuid.UUID(company_id),
                User.role == "driver",
                User.deleted_at.is_(None),
            )
        )
        return list(result)

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
