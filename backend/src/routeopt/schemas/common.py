"""Shared value objects reused across modules."""

from enum import Enum

from pydantic import BaseModel, Field


class GeoPoint(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    GEOCODED = "geocoded"
    ASSIGNED = "assigned"
    EN_ROUTE = "en_route"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"
