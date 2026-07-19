"""Auth endpoints — docs/ARCHITECTURE.md §2.2."""

from fastapi import APIRouter

from routeopt.modules.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from routeopt.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
service = AuthService()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterRequest) -> TokenResponse:
    return await service.register(payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest) -> TokenResponse:
    return await service.login(payload)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest) -> TokenResponse:
    return await service.refresh(payload)
