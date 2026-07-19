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


class VehicleOut(VehicleIn):
    id: str
    active: bool
