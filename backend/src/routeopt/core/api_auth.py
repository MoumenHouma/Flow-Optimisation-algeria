"""API-key authentication for the public API (F10, ARCHITECTURE §5.1).

Partners authenticate with ``X-API-Key: rk_live_...``. Only the SHA-256 hash is
stored, so the header is hashed and looked up. Scopes are hierarchical:
``read`` < ``write`` < ``admin``.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.exceptions import AuthError
from routeopt.core.security import hash_token
from routeopt.database import get_session
from routeopt.models.api_key import ApiKey

_SCOPE_RANK = {"read": 1, "write": 2, "admin": 3}


@dataclass
class ApiClient:
    company_id: str
    scope: str
    key_id: str


async def get_api_client(
    session: Annotated[AsyncSession, Depends(get_session)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> ApiClient:
    if not x_api_key:
        raise AuthError("Missing API key")
    key = await session.scalar(select(ApiKey).where(ApiKey.key_hash == hash_token(x_api_key)))
    now = datetime.now(UTC)
    if key is None or key.revoked_at is not None:
        raise AuthError("Invalid API key")
    if key.expires_at is not None and key.expires_at <= now:
        raise AuthError("API key expired")

    key.last_used_at = now
    await session.commit()
    return ApiClient(company_id=str(key.company_id), scope=key.scope, key_id=str(key.id))


def require_scope(minimum: str) -> Callable[[ApiClient], Awaitable[ApiClient]]:
    """Dependency factory enforcing the key has at least ``minimum`` scope."""
    needed = _SCOPE_RANK[minimum]

    async def _check(client: Annotated[ApiClient, Depends(get_api_client)]) -> ApiClient:
        if _SCOPE_RANK.get(client.scope, 0) < needed:
            raise AuthError(f"API key requires '{minimum}' scope")
        return client

    return _check
