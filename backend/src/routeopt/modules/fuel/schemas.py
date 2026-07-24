"""Fuel-station DTOs (F20)."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from routeopt.schemas.common import GeoPoint


class FuelStationIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    location: GeoPoint
    fuel_types: str = "essence"  # comma-separated: essence,diesel,gpl,electric
    status: Literal["available", "shortage", "closed"] = "available"
    notes: str | None = None


class FuelStatusIn(BaseModel):
    status: Literal["available", "shortage", "closed"]


class FuelStationOut(BaseModel):
    id: str
    name: str
    location: GeoPoint
    fuel_types: str
    status: str
    notes: str | None

    @classmethod
    def from_model(cls, s: Any) -> "FuelStationOut":
        return cls(
            id=str(s.id),
            name=s.name,
            location=GeoPoint(lat=float(s.lat), lon=float(s.lon)),
            fuel_types=s.fuel_types,
            status=s.status,
            notes=s.notes,
        )
