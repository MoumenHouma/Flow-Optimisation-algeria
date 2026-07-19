from typing import Any

from pydantic import BaseModel, Field

from routeopt.schemas.common import GeoPoint


class VehicleIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    vehicle_type: str = "car"  # car | van | truck | motorcycle
    license_plate: str | None = None
    capacity_weight: float = Field(1000, ge=0)
    capacity_volume: float = Field(10, ge=0)
    depot: GeoPoint
    depot_address: str
    driver_user_id: str | None = None


class FleetSummary(BaseModel):
    plan: str
    vehicle_count: int
    max_vehicles: int | None  # None => unlimited (Enterprise)


class VehicleOut(BaseModel):
    id: str
    name: str
    vehicle_type: str
    license_plate: str | None
    capacity_weight: float
    capacity_volume: float
    depot: GeoPoint
    depot_address: str
    active: bool

    @classmethod
    def from_model(cls, v: Any) -> "VehicleOut":
        return cls(
            id=str(v.id),
            name=v.name,
            vehicle_type=v.vehicle_type,
            license_plate=v.license_plate,
            capacity_weight=float(v.capacity_weight),
            capacity_volume=float(v.capacity_volume),
            depot=GeoPoint(lat=float(v.depot_lat), lon=float(v.depot_lon)),
            depot_address=v.depot_address,
            active=v.active,
        )
