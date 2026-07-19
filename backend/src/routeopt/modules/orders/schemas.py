from datetime import time

from pydantic import BaseModel, Field

from routeopt.schemas.common import DeliveryStatus


class DeliveryIn(BaseModel):
    order_id: str | None = None
    address: str = Field(..., min_length=1)
    address_locale: str = "fr"
    customer_phone: str | None = None
    time_window_start: time | None = None
    time_window_end: time | None = None
    service_time: int = 300
    weight: float = Field(0, ge=0)
    volume: float = Field(0, ge=0)
    priority: int = Field(1, ge=1, le=3)


class DeliveryOut(DeliveryIn):
    id: str
    lat: float | None = None
    lon: float | None = None
    geocoding_status: str
    status: DeliveryStatus


class BulkImportResponse(BaseModel):
    imported: int
    failed: int
    deliveries: list[DeliveryOut]
