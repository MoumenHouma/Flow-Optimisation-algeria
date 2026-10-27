from typing import Any

from pydantic import BaseModel, Field

from routeopt.schemas.common import GeoPoint


class VehicleIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    vehicle_type: str = "car"  # car | van | truck | motorcycle
    license_plate: str | None = None
    capacity_weight: float = Field(1000, ge=0)
    capacity_volume: float = Field(10, ge=0)
    # F20 fuel-shortage: optional range cap + fuel type.
    fuel_range_km: float | None = Field(None, gt=0)
    fuel_type: str = "essence"  # essence | diesel | gpl | electric
    # F12: provide either a depot_id (multi-dépôt) or an inline depot + address.
    depot_id: str | None = None
    depot: GeoPoint | None = None
    depot_address: str | None = None
    driver_user_id: str | None = None


class DepotIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    location: GeoPoint
    address: str = Field(..., min_length=1)
    active: bool = True


class DepotOut(BaseModel):
    id: str
    name: str
    location: GeoPoint
    address: str
    active: bool

    @classmethod
    def from_model(cls, d: Any) -> "DepotOut":
        return cls(
            id=str(d.id),
            name=d.name,
            location=GeoPoint(lat=float(d.lat), lon=float(d.lon)),
            address=d.address,
            active=d.active,
        )


class FleetSummary(BaseModel):
    plan: str
    vehicle_count: int
    max_vehicles: int | None  # None => unlimited (Enterprise)


class DriverIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: str | None = None


class DriverOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str

    @classmethod
    def from_model(cls, u: Any) -> "DriverOut":
        return cls(id=str(u.id), email=u.email, full_name=u.full_name, role=u.role)


class VehicleOut(BaseModel):
    id: str
    name: str
    vehicle_type: str
    license_plate: str | None
    capacity_weight: float
    capacity_volume: float
    fuel_range_km: float | None
    fuel_type: str
    depot_id: str | None
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
            fuel_range_km=float(v.fuel_range_km) if v.fuel_range_km is not None else None,
            fuel_type=v.fuel_type,
            depot_id=str(v.depot_id) if v.depot_id else None,
            depot=GeoPoint(lat=float(v.depot_lat), lon=float(v.depot_lon)),
            depot_address=v.depot_address,
            active=v.active,
        )
