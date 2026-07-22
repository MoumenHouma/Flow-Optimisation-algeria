from typing import Any

from pydantic import BaseModel, Field

from routeopt.schemas.common import GeoPoint, JobStatus


class OptimizationConstraints(BaseModel):
    respect_time_windows: bool = True
    respect_capacity: bool = True
    respect_priority: bool = True
    minimize_vehicles: bool = False


class ObjectiveWeights(BaseModel):
    """Relative weights for the multi-objective cost (F14). Distance-only default."""

    distance: float = Field(1.0, ge=0)
    time: float = Field(0.0, ge=0)
    fuel: float = Field(0.0, ge=0)
    co2: float = Field(0.0, ge=0)


class OptimizeRequest(BaseModel):
    # Empty lists mean "all routable deliveries" / "all active vehicles".
    delivery_ids: list[str] = Field(default_factory=list, max_length=500)
    vehicle_ids: list[str] = Field(default_factory=list, max_length=50)
    depot: GeoPoint | None = None
    constraints: OptimizationConstraints = OptimizationConstraints()
    objective: ObjectiveWeights = ObjectiveWeights()


class ReoptimizeRequest(BaseModel):
    # The driver's live position becomes the start of the re-planned leg (F9);
    # falls back to the vehicle depot when omitted.
    current_lat: float | None = None
    current_lon: float | None = None
    constraints: OptimizationConstraints = OptimizationConstraints()
    objective: ObjectiveWeights = ObjectiveWeights()


class OptimizeResponse(BaseModel):
    job_id: str
    status: JobStatus
    estimated_duration_ms: int


class JobOut(BaseModel):
    job_id: str
    status: JobStatus
    delivery_count: int | None = None
    vehicle_count: int | None = None
    solver_strategy: str | None = None
    duration_ms: int | None = None
    total_distance_m: float | None = None
    total_fuel_l: float | None = None
    total_co2_kg: float | None = None
    route_ids: list[str] = Field(default_factory=list)
    error_message: str | None = None


class RouteStopOut(BaseModel):
    delivery_id: str
    sequence: int
    eta: str | None = None
    lat: float | None = None
    lon: float | None = None
    address: str | None = None


class RouteOut(BaseModel):
    id: str
    vehicle_id: str | None
    total_distance_m: float | None
    total_time_s: int | None
    status: str
    depot: GeoPoint | None = None
    # GeoJSON LineString of the road path when available (OSRM /route); the client
    # falls back to straight lines between stops otherwise.
    geometry: dict[str, Any] | None = None
    stops: list[RouteStopOut]
