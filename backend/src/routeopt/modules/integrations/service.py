"""API-key + webhook management (F10). JWT-authed (admin) management plane."""

import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.crypto import encrypt
from routeopt.core.exceptions import NotFoundError, ValidationError
from routeopt.core.security import hash_token
from routeopt.models.api_key import ApiKey
from routeopt.models.webhook import Webhook
from routeopt.modules.integrations.schemas import (
    ALLOWED_EVENTS,
    ApiKeyCreate,
    WebhookCreate,
)

_KEY_PREFIX = "rk_live_"


def generate_api_key() -> tuple[str, str, str]:
    """Return (plaintext, key_prefix, key_hash) for a fresh partner key."""
    plaintext = _KEY_PREFIX + secrets.token_hex(16)
    return plaintext, plaintext[:12], hash_token(plaintext)


class IntegrationsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_api_key(self, company_id: str, payload: ApiKeyCreate) -> tuple[ApiKey, str]:
        plaintext, prefix, key_hash = generate_api_key()
        key = ApiKey(
            company_id=uuid.UUID(company_id),
            name=payload.name,
            key_hash=key_hash,
            key_prefix=prefix,
            scope=payload.scope,
        )
        self.session.add(key)
        await self.session.commit()
        await self.session.refresh(key)
        return key, plaintext

    async def list_api_keys(self, company_id: str) -> list[ApiKey]:
        rows = await self.session.scalars(
            select(ApiKey)
            .where(ApiKey.company_id == uuid.UUID(company_id))
            .order_by(ApiKey.created_at.desc())
        )
        return list(rows)

    async def revoke_api_key(self, company_id: str, key_id: str) -> None:
        key = await self.session.get(ApiKey, uuid.UUID(key_id))
        if key is None or str(key.company_id) != company_id:
            raise NotFoundError("API key not found")
        if key.revoked_at is None:
            key.revoked_at = datetime.now(UTC)
            await self.session.commit()

    async def create_webhook(self, company_id: str, payload: WebhookCreate) -> tuple[Webhook, str]:
        invalid = [e for e in payload.events if e != "*" and e not in ALLOWED_EVENTS]
        if invalid:
            raise ValidationError(f"Unknown event(s): {', '.join(invalid)}")
        secret = secrets.token_hex(32)
        webhook = Webhook(
            company_id=uuid.UUID(company_id),
            url=str(payload.url),
            secret=encrypt(secret),  # stored encrypted; plaintext returned once
            events=",".join(payload.events),
            active=True,
        )
        self.session.add(webhook)
        await self.session.commit()
        await self.session.refresh(webhook)
        return webhook, secret

    async def list_webhooks(self, company_id: str) -> list[Webhook]:
        rows = await self.session.scalars(
            select(Webhook)
            .where(Webhook.company_id == uuid.UUID(company_id))
            .order_by(Webhook.created_at.desc())
        )
        return list(rows)

    async def delete_webhook(self, company_id: str, webhook_id: str) -> None:
        webhook = await self.session.get(Webhook, uuid.UUID(webhook_id))
        if webhook is None or str(webhook.company_id) != company_id:
            raise NotFoundError("Webhook not found")
        await self.session.delete(webhook)
        await self.session.commit()
