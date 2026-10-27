"""Auth business logic — registration, login, refresh-token rotation.

Persists Company + User (SCHEMA.md §3.1, §3.2) and revocable refresh tokens
(§3.3). Refresh tokens are rotated on every use: the presented token is revoked
and a fresh pair is issued, so a stolen-then-replayed token is caught.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.config import get_settings
from routeopt.core import audit
from routeopt.core.email import send_password_reset
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
from routeopt.models.password_reset import PasswordResetToken
from routeopt.models.refresh_token import RefreshToken
from routeopt.models.user import User
from routeopt.modules.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
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

        tokens = await self._issue_and_store(user, uuid.uuid4())
        await self.session.commit()
        return tokens

    async def login(self, payload: LoginRequest, ip: str | None = None) -> TokenResponse:
        user = await self._get_user_by_email(payload.email.lower())
        if user is None or not verify_password(payload.password, user.password_hash):
            raise AuthError("Invalid email or password")
        if not user.active:
            raise AuthError("Account is disabled")
        user.last_login_at = datetime.now(UTC)
        tokens = await self._issue_and_store(user, uuid.uuid4())
        await audit.record(
            self.session,
            action="user.login",
            resource_type="user",
            company_id=user.company_id,
            actor_user_id=user.id,
            resource_id=user.id,
            ip_address=ip,
        )
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
        if stored is None or stored.expires_at < now:
            raise AuthError("Refresh token expired or revoked")

        if stored.revoked_at is not None:
            # Reuse of an already-rotated token → likely theft. Revoke the whole
            # family so no descendant token remains valid (M3, OWASP reuse detection).
            await self._revoke_family(stored.family_id, now)
            await self.session.commit()
            raise AuthError("Refresh token reuse detected")

        stored.revoked_at = now  # rotate: single-use refresh tokens
        user = await self.session.get(User, stored.user_id)
        if user is None or not user.active:
            raise AuthError("User no longer active")
        tokens = await self._issue_and_store(user, stored.family_id)
        await self.session.commit()
        return tokens

    async def logout(self, payload: LogoutRequest) -> None:
        """Revoke the presented refresh token and its whole family (M3).

        Idempotent: an unknown or malformed token is a no-op — logout should
        never error. The short-lived access token (15 min) is not revoked here;
        it simply expires.
        """
        try:
            claims = decode_token(payload.refresh_token)
        except Exception:  # noqa: BLE001 - any decode failure is a silent no-op
            return
        if claims.get("type") != "refresh":
            return
        stored = await self.session.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(payload.refresh_token))
        )
        if stored is not None:
            await self._revoke_family(stored.family_id, datetime.now(UTC))
            await self.session.commit()

    async def request_password_reset(
        self, payload: ForgotPasswordRequest, ip: str | None = None
    ) -> None:
        """Issue a single-use reset link and mail it. Always silent on the outcome.

        An unknown or disabled account is a no-op: the endpoint must not reveal
        whether an email is registered (user enumeration).
        """
        user = await self._get_user_by_email(payload.email.lower())
        if user is None or not user.active:
            return
        token = secrets.token_urlsafe(32)
        self.session.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(token),
                expires_at=datetime.now(UTC)
                + timedelta(minutes=settings.password_reset_expire_minutes),
            )
        )
        await audit.record(
            self.session,
            action="user.password_reset_requested",
            resource_type="user",
            company_id=user.company_id,
            actor_user_id=user.id,
            resource_id=user.id,
            ip_address=ip,
        )
        await self.session.commit()
        # After commit: a delivery failure must not roll back a valid token.
        await send_password_reset(user.email, token)

    async def reset_password(self, payload: ResetPasswordRequest, ip: str | None = None) -> None:
        """Consume a reset token, set the new password and kill every session."""
        now = datetime.now(UTC)
        stored = await self.session.scalar(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == hash_token(payload.token)
            )
        )
        if stored is None or stored.used_at is not None or stored.expires_at < now:
            raise AuthError("Invalid or expired reset token")
        user = await self.session.get(User, stored.user_id)
        if user is None or not user.active or user.deleted_at is not None:
            raise AuthError("Invalid or expired reset token")

        user.password_hash = hash_password(payload.password)
        stored.used_at = now
        # Any other outstanding link for this user is void once one is used.
        await self.session.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=now)
        )
        # A password change ends every session, not just the current family.
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await audit.record(
            self.session,
            action="user.password_reset",
            resource_type="user",
            company_id=user.company_id,
            actor_user_id=user.id,
            resource_id=user.id,
            ip_address=ip,
        )
        await self.session.commit()

    # ── helpers ──────────────────────────────────────────────────────────
    async def _revoke_family(self, family_id: uuid.UUID, now: datetime) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    async def _get_user_by_email(self, email: str) -> User | None:
        user: User | None = await self.session.scalar(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        return user

    async def _issue_and_store(self, user: User, family_id: uuid.UUID) -> TokenResponse:
        if user.role not in _VALID_ROLES:
            raise AuthError("Unknown role")
        # Include the plan so rate limits are plan-aware without a per-request DB hit.
        company = await self.session.get(Company, user.company_id)
        plan = company.plan if company else "free"
        claims = {
            "sub": str(user.id),
            "company_id": str(user.company_id),
            "role": user.role,
            "plan": plan,
        }
        access = create_access_token(claims)
        refresh = create_refresh_token(claims)
        self.session.add(
            RefreshToken(
                user_id=user.id,
                family_id=family_id,
                token_hash=hash_token(refresh),
                expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
            )
        )
        return TokenResponse(access_token=access, refresh_token=refresh)
