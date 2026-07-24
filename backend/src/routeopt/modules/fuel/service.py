"""Fuel-station logic (F20): CRUD + live status updates, tenant-scoped."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.exceptions import NotFoundError
from routeopt.models.fuel_station import FuelStation
from routeopt.modules.fuel.schemas import FuelStationIn, FuelStationOut, FuelStatusIn


class FuelService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_stations(self, company_id: str) -> list[FuelStationOut]:
        rows = await self.session.scalars(
            select(FuelStation)
            .where(
                FuelStation.company_id == uuid.UUID(company_id),
                FuelStation.deleted_at.is_(None),
            )
            .order_by(FuelStation.name)
        )
        return [FuelStationOut.from_model(s) for s in rows]

    async def create_station(self, company_id: str, payload: FuelStationIn) -> FuelStationOut:
        station = FuelStation(
            company_id=uuid.UUID(company_id),
            name=payload.name,
            lat=payload.location.lat,
            lon=payload.location.lon,
            fuel_types=payload.fuel_types,
            status=payload.status,
            notes=payload.notes,
        )
        self.session.add(station)
        await self.session.commit()
        await self.session.refresh(station)
        return FuelStationOut.from_model(station)

    async def _scoped(self, company_id: str, station_id: str) -> FuelStation:
        station = await self.session.get(FuelStation, uuid.UUID(station_id))
        if (
            station is None
            or str(station.company_id) != company_id
            or station.deleted_at is not None
        ):
            raise NotFoundError("Fuel station not found")
        return station

    async def set_status(
        self, company_id: str, station_id: str, payload: FuelStatusIn
    ) -> FuelStationOut:
        station = await self._scoped(company_id, station_id)
        station.status = payload.status
        await self.session.commit()
        await self.session.refresh(station)
        return FuelStationOut.from_model(station)

    async def delete_station(self, company_id: str, station_id: str) -> None:
        station = await self._scoped(company_id, station_id)
        station.deleted_at = datetime.now(UTC)
        await self.session.commit()
