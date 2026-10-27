"""Tracking DTOs (F18)."""

from pydantic import BaseModel, Field


class PositionIn(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class PositionOut(BaseModel):
    vehicle_id: str
    lat: float
    lon: float
    ts: float  # epoch seconds when the position was recorded


class TrackOut(BaseModel):
    """Public, PII-free view of a delivery for the customer tracking link."""

    order_id: str | None
    status: str
    vehicle_position: PositionOut | None
