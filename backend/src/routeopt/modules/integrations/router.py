"""Integration management endpoints (F10) — API keys + webhooks (admin, JWT)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core import audit
from routeopt.core.audit import client_ip
from routeopt.core.dependencies import CurrentUser, require_roles
from routeopt.database import get_session
from routeopt.modules.integrations.schemas import (
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyOut,
    WebhookCreate,
    WebhookCreated,
    WebhookOut,
)
from routeopt.modules.integrations.service import IntegrationsService

router = APIRouter(prefix="/integrations", tags=["integrations"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
AdminDep = Annotated[CurrentUser, Depends(require_roles("admin"))]


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=201)
async def create_api_key(
    payload: ApiKeyCreate, session: SessionDep, user: AdminDep, request: Request
) -> ApiKeyCreated:
    """Create a partner API key. The plaintext key is returned only once."""
    key, plaintext = await IntegrationsService(session).create_api_key(user.company_id, payload)
    await audit.record(
        session,
        action="api_key.created",
        resource_type="api_key",
        company_id=user.company_id,
        actor_user_id=user.user_id,
        resource_id=key.id,
        metadata={"name": payload.name},
        ip_address=client_ip(request),
    )
    await session.commit()
    return ApiKeyCreated(**ApiKeyOut.from_model(key).model_dump(), key=plaintext)


@router.get("/api-keys", response_model=list[ApiKeyOut])
async def list_api_keys(session: SessionDep, user: AdminDep) -> list[ApiKeyOut]:
    keys = await IntegrationsService(session).list_api_keys(user.company_id)
    return [ApiKeyOut.from_model(k) for k in keys]


@router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str, session: SessionDep, user: AdminDep, request: Request
) -> Response:
    await IntegrationsService(session).revoke_api_key(user.company_id, key_id)
    await audit.record(
        session,
        action="api_key.revoked",
        resource_type="api_key",
        company_id=user.company_id,
        actor_user_id=user.user_id,
        resource_id=key_id,
        ip_address=client_ip(request),
    )
    await session.commit()
    return Response(status_code=204)


@router.post("/webhooks", response_model=WebhookCreated, status_code=201)
async def create_webhook(
    payload: WebhookCreate, session: SessionDep, user: AdminDep, request: Request
) -> WebhookCreated:
    """Register a webhook endpoint. The signing secret is returned only once."""
    webhook, secret = await IntegrationsService(session).create_webhook(user.company_id, payload)
    await audit.record(
        session,
        action="webhook.created",
        resource_type="webhook",
        company_id=user.company_id,
        actor_user_id=user.user_id,
        resource_id=webhook.id,
        metadata={"url": str(payload.url), "events": payload.events},
        ip_address=client_ip(request),
    )
    await session.commit()
    return WebhookCreated(**WebhookOut.from_model(webhook).model_dump(), secret=secret)


@router.get("/webhooks", response_model=list[WebhookOut])
async def list_webhooks(session: SessionDep, user: AdminDep) -> list[WebhookOut]:
    hooks = await IntegrationsService(session).list_webhooks(user.company_id)
    return [WebhookOut.from_model(w) for w in hooks]


@router.delete("/webhooks/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: str, session: SessionDep, user: AdminDep, request: Request
) -> Response:
    await IntegrationsService(session).delete_webhook(user.company_id, webhook_id)
    await audit.record(
        session,
        action="webhook.deleted",
        resource_type="webhook",
        company_id=user.company_id,
        actor_user_id=user.user_id,
        resource_id=webhook_id,
        ip_address=client_ip(request),
    )
    await session.commit()
    return Response(status_code=204)
