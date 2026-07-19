"""Auth business logic — registration, login, refresh-token rotation.

Persists Company + User (SCHEMA.md §3.1, §3.2) and revocable refresh tokens
(§3.3). Refresh tokens are rotated on every use: the presented token is revoked
and a fresh pair is issued, so a stolen-then-replayed token is caught.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.config import get_settings
from routeopt.core.exceptions import AuthError, ConflictError
from routeopt.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from routeopt.models.company import Company
from routeopt.models.refresh_token import RefreshToken
from routeopt.models.user import User
from routeopt.modules.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)

settings = get_settings()
_VALID_ROLES = {"admin", "manager", "driver", "viewer"}


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register(self, payload: RegisterRequest) -> TokenResponse:
        """Create a company + its first (admin) user, then issue tokens."""
        company = Company(name=payload.company_name)  # plan/quotas default to free tier
        self.session.add(company)
        await self.session.flush()  # assign company.id

        user = User(
            company_id=company.id,
            email=payload.email.lower(),
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            role="admin",
        )
        self.session.add(user)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Email already registered") from exc

        tokens = await self._issue_and_store(user)
        await self.session.commit()
        return tokens

    async def login(self, payload: LoginRequest) -> TokenResponse:
        user = await self._get_user_by_email(payload.email.lower())
        if user is None or not verify_password(payload.password, user.password_hash):
            raise AuthError("Invalid email or password")
        if not user.active:
            raise AuthError("Account is disabled")
        user.last_login_at = datetime.now(UTC)
        tokens = await self._issue_and_store(user)
        await self.session.commit()
        return tokens

    async def refresh(self, payload: RefreshRequest) -> TokenResponse:
        try:
            claims = decode_token(payload.refresh_token)
        except Exception as exc:  # jwt.PyJWTError and friends
            raise AuthError("Invalid refresh token") from exc
        if claims.get("type") != "refresh":
            raise AuthError("Wrong token type")

        token_hash = hash_token(payload.refresh_token)
        stored = await self.session.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        now = datetime.now(UTC)
        if stored is None or stored.revoked_at is not None or stored.expires_at < now:
            raise AuthError("Refresh token expired or revoked")

        stored.revoked_at = now  # rotate: single-use refresh tokens
        user = await self.session.get(User, stored.user_id)
        if user is None or not user.active:
            raise AuthError("User no longer active")
        tokens = await self._issue_and_store(user)
        await self.session.commit()
        return tokens

    # ── helpers ──────────────────────────────────────────────────────────
    async def _get_user_by_email(self, email: str) -> User | None:
        return await self.session.scalar(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )

    async def _issue_and_store(self, user: User) -> TokenResponse:
        if user.role not in _VALID_ROLES:
            raise AuthError("Unknown role")
        claims = {"sub": str(user.id), "company_id": str(user.company_id), "role": user.role}
        access = create_access_token(claims)
        refresh = create_refresh_token(claims)
        self.session.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(refresh),
                expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
            )
        )
        return TokenResponse(access_token=access, refresh_token=refresh)
