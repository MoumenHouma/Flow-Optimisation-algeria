"""Shared FastAPI dependencies: auth, RBAC, rate limiting.

RBAC roles (docs/ARCHITECTURE.md §2.2): admin, manager, driver, viewer.
Multi-tenant isolation: every request carries company_id, enforced per-resource.
Rate limits are per-plan (PRD §5.1), read from the JWT `plan` claim.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header

from routeopt.core.exceptions import AuthError, RateLimitError
from routeopt.core.security import decode_token
from routeopt.redis_client import redis_client

# Requests/minute by plan (PRD §5.1). None = unlimited (Enterprise).
_PLAN_LIMITS: dict[str, int | None] = {
    "free": 10,
    "starter": 100,
    "pro": 1000,
    "enterprise": None,
}


@dataclass
class CurrentUser:
    user_id: str
    company_id: str
    role: str
    plan: str = "free"


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthError("Missing bearer token")
    token = authorization.removeprefix("Bearer ")
    try:
        claims = decode_token(token)
    except jwt.PyJWTError as exc:  # pragma: no cover - thin wrapper
        raise AuthError("Invalid token") from exc
    if claims.get("type") != "access":
        raise AuthError("Wrong token type")
    return CurrentUser(
        user_id=claims["sub"],
        company_id=claims["company_id"],
        role=claims["role"],
        plan=claims.get("plan", "free"),  # default keeps pre-plan tokens working
    )


def require_roles(*roles: str) -> Callable[[CurrentUser], Awaitable[CurrentUser]]:
    """Dependency factory enforcing that the caller has one of `roles`."""

    async def _check(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if user.role not in roles:
            raise AuthError(f"Requires one of roles: {', '.join(roles)}")
        return user

    return _check


async def rate_limiter(user: Annotated[CurrentUser, Depends(get_current_user)]) -> None:
    """Fixed-window per-plan rate limit keyed on company (docs/SCHEMA.md §7)."""
    limit = _PLAN_LIMITS.get(user.plan, _PLAN_LIMITS["free"])
    if limit is None:  # unlimited (Enterprise)
        return
    key = f"ratelimit:{user.company_id}:{_current_minute()}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, 60)
    if count > limit:
        raise RateLimitError()


def _current_minute() -> int:
    from time import time

    return int(time() // 60)
