"""Company / white-label DTOs (F16)."""

import re
from typing import Any

from pydantic import BaseModel, field_validator

_HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


class Branding(BaseModel):
    brand_name: str | None = None
    primary_color: str | None = None  # hex, e.g. "#2563EB"
    logo_url: str | None = None

    @field_validator("primary_color")
    @classmethod
    def _valid_hex(cls, v: str | None) -> str | None:
        if v is not None and not _HEX.match(v):
            raise ValueError("primary_color must be a hex colour like #2563EB")
        return v


class CompanyOut(BaseModel):
    id: str
    name: str
    plan: str
    locale: str
    branding: Branding | None

    @classmethod
    def from_model(cls, c: Any) -> "CompanyOut":
        return cls(
            id=str(c.id),
            name=c.name,
            plan=c.plan,
            locale=c.locale,
            branding=Branding(**c.branding) if c.branding else None,
        )
