"""Territory DTOs (F15)."""

from typing import Any

from pydantic import BaseModel, Field

from routeopt.schemas.common import GeoPoint


class TerritoryIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field("#2563EB", max_length=9)
    driver_user_id: str | None = None


class TerritoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    color: str | None = Field(None, max_length=9)
    driver_user_id: str | None = None


class TerritoryOut(BaseModel):
    id: str
    name: str
    color: str
    driver_user_id: str | None
    centroid: GeoPoint | None
    delivery_count: int

    @classmethod
    def from_model(cls, t: Any, delivery_count: int = 0) -> "TerritoryOut":
        centroid = (
            GeoPoint(lat=float(t.centroid_lat), lon=float(t.centroid_lon))
            if t.centroid_lat is not None and t.centroid_lon is not None
            else None
        )
        return cls(
            id=str(t.id),
            name=t.name,
            color=t.color,
            driver_user_id=str(t.driver_user_id) if t.driver_user_id else None,
            centroid=centroid,
            delivery_count=delivery_count,
        )


class AutoGenerateRequest(BaseModel):
    # Number of zones; defaults to the active-vehicle count when omitted.
    zones: int | None = Field(None, ge=1, le=50)
