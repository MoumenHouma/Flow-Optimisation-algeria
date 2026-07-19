from typing import Literal

from pydantic import BaseModel

from routeopt.schemas.common import DeliveryStatus


class DriverStopOut(BaseModel):
    delivery_id: str
    sequence: int
    address: str
    lat: float | None
    lon: float | None
    customer_phone: str | None
    time_window_start: str | None
    time_window_end: str | None
    status: DeliveryStatus


class DriverRouteOut(BaseModel):
    route_id: str
    vehicle_name: str | None
    total_distance_m: float | None
    delivered: int
    total: int
    stops: list[DriverStopOut]


class StatusUpdate(BaseModel):
    # Transitions a driver can make from the field.
    status: Literal["en_route", "delivered", "failed"]
    reason: str | None = None
    lat: float | None = None
    lon: float | None = None
