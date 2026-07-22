"""Public API DTOs (F10) — the e-commerce integration surface."""

from datetime import time
from typing import Any

from pydantic import BaseModel, Field


class PublicDeliveryIn(BaseModel):
    """Create a delivery from an external system (Shopify/WooCommerce/…)."""

    order_id: str | None = Field(None, max_length=100)
    address: str = Field(..., min_length=1)
    address_locale: str = "fr"
    # If lat/lon are provided, geocoding is skipped; otherwise it's resolved async.
    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)
    customer_phone: str | None = Field(None, max_length=30)
    time_window_start: time | None = None
    time_window_end: time | None = None
    weight: float = Field(0, ge=0)
    priority: int = Field(1, ge=1, le=3)


class PublicDeliveryOut(BaseModel):
    id: str
    order_id: str | None
    address: str
    lat: float | None
    lon: float | None
    geocoding_status: str
    status: str
    created_at: str

    @classmethod
    def from_model(cls, d: Any) -> "PublicDeliveryOut":
        return cls(
            id=str(d.id),
            order_id=d.order_id,
            address=d.address,
            lat=float(d.lat) if d.lat is not None else None,
            lon=float(d.lon) if d.lon is not None else None,
            geocoding_status=d.geocoding_status,
            status=d.status,
            created_at=d.created_at.isoformat(),
        )
