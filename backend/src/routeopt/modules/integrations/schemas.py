"""Integration management DTOs (F10): API keys + webhooks."""

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl

# Events a webhook may subscribe to (also accepted: "*" for all).
ALLOWED_EVENTS = ("delivery.status_changed", "optimization.completed")

Scope = Literal["read", "write", "admin"]


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scope: Scope = "read"


class ApiKeyOut(BaseModel):
    id: str
    name: str
    key_prefix: str
    scope: str
    last_used_at: str | None
    revoked_at: str | None
    created_at: str

    @classmethod
    def from_model(cls, k: Any) -> "ApiKeyOut":
        return cls(
            id=str(k.id),
            name=k.name,
            key_prefix=k.key_prefix,
            scope=k.scope,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
            revoked_at=k.revoked_at.isoformat() if k.revoked_at else None,
            created_at=k.created_at.isoformat(),
        )


class ApiKeyCreated(ApiKeyOut):
    # The plaintext key — shown once at creation, never retrievable again.
    key: str


class WebhookCreate(BaseModel):
    url: HttpUrl
    events: list[str] = Field(..., min_length=1)


class WebhookOut(BaseModel):
    id: str
    url: str
    events: list[str]
    active: bool
    created_at: str

    @classmethod
    def from_model(cls, w: Any) -> "WebhookOut":
        return cls(
            id=str(w.id),
            url=w.url,
            events=[e for e in w.events.split(",") if e],
            active=w.active,
            created_at=w.created_at.isoformat(),
        )


class WebhookCreated(WebhookOut):
    # The signing secret — shown once at creation.
    secret: str
