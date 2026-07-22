from datetime import time
from typing import Any

from pydantic import BaseModel, Field

from routeopt.schemas.common import DeliveryStatus


class DeliveryIn(BaseModel):
    order_id: str | None = None
    address: str = Field(..., min_length=1)
    address_locale: str = "fr"
    # If lat/lon are supplied, geocoding is skipped (status=matched). Otherwise the
    # delivery is stored pending geocoding (F2, Nominatim) — see OrdersService.
    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)
    customer_phone: str | None = None
    time_window_start: time | None = None
    time_window_end: time | None = None
    service_time: int = 300
    weight: float = Field(0, ge=0)
    volume: float = Field(0, ge=0)
    priority: int = Field(1, ge=1, le=3)
    # F17 cash-on-delivery: order total due at the stop (NULL/0 = prepaid).
    cod_amount: float | None = Field(None, ge=0)
    cod_currency: str = "DZD"


class DeliveryOut(BaseModel):
    id: str
    order_id: str | None
    address: str
    lat: float | None
    lon: float | None
    geocoding_status: str
    status: DeliveryStatus
    weight: float
    volume: float
    priority: int
    cod_amount: float | None
    cod_currency: str

    @classmethod
    def from_model(cls, d: Any) -> "DeliveryOut":
        return cls(
            id=str(d.id),
            order_id=d.order_id,
            address=d.address,
            lat=float(d.lat) if d.lat is not None else None,
            lon=float(d.lon) if d.lon is not None else None,
            geocoding_status=d.geocoding_status,
            status=DeliveryStatus(d.status),
            weight=float(d.weight),
            volume=float(d.volume),
            priority=d.priority,
            cod_amount=float(d.cod_amount) if d.cod_amount is not None else None,
            cod_currency=d.cod_currency,
        )


class BulkCreateResponse(BaseModel):
    created: int
    geocoding_pending: int
    deliveries: list[DeliveryOut]
