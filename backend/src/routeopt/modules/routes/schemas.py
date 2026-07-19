from pydantic import BaseModel, Field

from routeopt.schemas.common import GeoPoint, JobStatus


class OptimizationConstraints(BaseModel):
    respect_time_windows: bool = True
    respect_capacity: bool = True
    respect_priority: bool = True
    minimize_vehicles: bool = False


class OptimizeRequest(BaseModel):
    delivery_ids: list[str] = Field(..., min_length=1, max_length=500)
    vehicle_ids: list[str] = Field(..., min_length=1, max_length=50)
    depot: GeoPoint | None = None
    constraints: OptimizationConstraints = OptimizationConstraints()


class OptimizeResponse(BaseModel):
    job_id: str
    status: JobStatus
    estimated_duration_ms: int


class RouteStopOut(BaseModel):
    delivery_id: str
    sequence: int
    eta: str | None = None


class RouteOut(BaseModel):
    id: str
    vehicle_id: str | None
    total_distance_m: float | None
    total_time_s: int | None
    status: str
    stops: list[RouteStopOut]
