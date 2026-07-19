"""Auth business logic. TODO: persist users/companies + refresh tokens (SCHEMA §3)."""

from routeopt.core.exceptions import AuthError
from routeopt.core.security import create_access_token, create_refresh_token
from routeopt.modules.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)


class AuthService:
    """Handles registration, login and token refresh.

    This is a scaffold: wire in the SQLAlchemy session and User/Company/
    RefreshToken models (docs/SCHEMA.md §3) to complete each method.
    """

    async def register(self, payload: RegisterRequest) -> TokenResponse:
        # TODO: create Company + User (role='admin'), hash password, persist.
        raise NotImplementedError("register: persist company + admin user")

    async def login(self, payload: LoginRequest) -> TokenResponse:
        # TODO: look up user by email, verify_password, issue tokens.
        raise NotImplementedError("login: verify credentials and issue tokens")

    async def refresh(self, payload: RefreshRequest) -> TokenResponse:
        # TODO: validate stored (hashed) refresh token, rotate it.
        raise NotImplementedError("refresh: rotate refresh token")

    def _issue_tokens(self, *, user_id: str, company_id: str, role: str) -> TokenResponse:
        claims = {"sub": user_id, "company_id": company_id, "role": role}
        if role not in {"admin", "manager", "driver", "viewer"}:
            raise AuthError("Unknown role")
        return TokenResponse(
            access_token=create_access_token(claims),
            refresh_token=create_refresh_token(claims),
        )
