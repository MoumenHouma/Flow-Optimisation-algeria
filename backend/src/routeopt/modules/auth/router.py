"""Auth endpoints — docs/ARCHITECTURE.md §2.2."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.audit import client_ip
from routeopt.core.dependencies import CurrentUser, enforce_fixed_window, get_current_user
from routeopt.database import get_session
from routeopt.modules.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from routeopt.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# Password-recovery endpoints are unauthenticated, so the limiter buckets on the
# caller's IP instead of the company (which only exists once you hold a token).
_RESET_REQUESTS_PER_MINUTE = 5


async def _throttle_by_ip(request: Request) -> None:
    await enforce_fixed_window(
        f"pwreset:{client_ip(request) or 'unknown'}", _RESET_REQUESTS_PER_MINUTE
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterRequest, session: SessionDep) -> TokenResponse:
    return await AuthService(session).register(payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: SessionDep, request: Request) -> TokenResponse:
    return await AuthService(session).login(payload, ip=client_ip(request))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, session: SessionDep) -> TokenResponse:
    return await AuthService(session).refresh(payload)


@router.post("/logout", status_code=204)
async def logout(payload: LogoutRequest, session: SessionDep) -> Response:
    """Revoke the presented refresh token and its family (M3). Always 204."""
    await AuthService(session).logout(payload)
    return Response(status_code=204)


@router.post("/forgot-password", status_code=202)
async def forgot_password(
    payload: ForgotPasswordRequest,
    session: SessionDep,
    request: Request,
    _: Annotated[None, Depends(_throttle_by_ip)],
) -> Response:
    """Mail a reset link. Always 202 — never reveals whether the email exists."""
    await AuthService(session).request_password_reset(payload, ip=client_ip(request))
    return Response(status_code=202)


@router.post("/reset-password", status_code=204)
async def reset_password(
    payload: ResetPasswordRequest,
    session: SessionDep,
    request: Request,
    _: Annotated[None, Depends(_throttle_by_ip)],
) -> Response:
    """Consume a reset token: sets the new password and revokes every session."""
    await AuthService(session).reset_password(payload, ip=client_ip(request))
    return Response(status_code=204)


@router.get("/me")
async def me(current: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, str]:
    """Return the authenticated principal (from the access-token claims)."""
    return {
        "user_id": current.user_id,
        "company_id": current.company_id,
        "role": current.role,
    }
