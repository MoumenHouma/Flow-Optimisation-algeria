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
    # F17: cash the driver must collect at this stop (null = prepaid).
    cod_amount: float | None
    cod_currency: str


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
    # F17: cash collected at this stop. Only recorded on a `delivered` update for
    # a delivery that has a cod_amount due. None = driver didn't report a figure.
    cod_collected: float | None = None
    cod_method: Literal["cash", "baridimob", "ccp", "none"] = "cash"


class ProofOut(BaseModel):
    delivery_id: str
    # Short-lived presigned URLs (or null if that artefact wasn't captured).
    photo_url: str | None
    signature_url: str | None
    lat: float | None
    lon: float | None
    captured_at: str
