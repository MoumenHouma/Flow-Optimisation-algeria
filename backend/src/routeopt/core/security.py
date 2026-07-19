"""Password hashing and JWT issuance/verification (docs/ARCHITECTURE.md §5.1).

JWTs are signed with RS256. Access tokens live 15 min, refresh tokens 7 days;
refresh tokens are persisted *hashed* (SCHEMA.md §3.3) so sessions are revocable.
"""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import bcrypt
import jwt

from routeopt.config import get_settings

settings = get_settings()


def hash_password(plain: str) -> str:
    # bcrypt caps input at 72 bytes; pre-hash so long passwords aren't truncated.
    digest = hashlib.sha256(plain.encode()).digest()
    return bcrypt.hashpw(digest, bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    digest = hashlib.sha256(plain.encode()).digest()
    return bcrypt.checkpw(digest, hashed.encode())


def hash_token(token: str) -> str:
    """SHA-256 of a token — refresh tokens are stored hashed, never in clear."""
    return hashlib.sha256(token.encode()).hexdigest()


@lru_cache
def _read_key(path: str) -> str:
    return Path(path).read_text()


def create_access_token(claims: dict[str, Any]) -> str:
    payload = {
        **claims,
        "type": "access",
        "jti": str(uuid.uuid4()),  # unique per token — avoids identical same-second tokens
        "exp": datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(
        payload, _read_key(settings.jwt_private_key_path), algorithm=settings.jwt_algorithm
    )


def create_refresh_token(claims: dict[str, Any]) -> str:
    payload = {
        **claims,
        "type": "refresh",
        "jti": str(uuid.uuid4()),  # unique per token — avoids hash collisions on reissue
        "exp": datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
    }
    return jwt.encode(
        payload, _read_key(settings.jwt_private_key_path), algorithm=settings.jwt_algorithm
    )


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        _read_key(settings.jwt_public_key_path),
        algorithms=[settings.jwt_algorithm],
    )
