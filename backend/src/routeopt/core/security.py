"""Password hashing and JWT issuance/verification (docs/ARCHITECTURE.md §5.1).

JWTs are signed with RS256. Access tokens live 15 min, refresh tokens 7 days;
refresh tokens are persisted hashed (SCHEMA.md §3.3) so sessions are revocable.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jwt
from passlib.context import CryptContext

from routeopt.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _read_key(path: str) -> str:
    return Path(path).read_text()


def create_access_token(claims: dict[str, Any]) -> str:
    payload = {
        **claims,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, _read_key(settings.jwt_private_key_path), algorithm=settings.jwt_algorithm)


def create_refresh_token(claims: dict[str, Any]) -> str:
    payload = {
        **claims,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    }
    return jwt.encode(payload, _read_key(settings.jwt_private_key_path), algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        _read_key(settings.jwt_public_key_path),
        algorithms=[settings.jwt_algorithm],
    )
