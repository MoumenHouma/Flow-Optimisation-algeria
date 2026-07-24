"""Auth endpoints — docs/ARCHITECTURE.md §2.2."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.audit import client_ip
from routeopt.core.dependencies import CurrentUser, get_current_user
from routeopt.database import get_session
from routeopt.modules.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from routeopt.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


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


@router.get("/me")
async def me(current: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, str]:
    """Return the authenticated principal (from the access-token claims)."""
    return {
        "user_id": current.user_id,
        "company_id": current.company_id,
        "role": current.role,
    }
