"""Unit tests for password hashing and JWT (docs/RULES.md §5.2). No DB needed."""

from datetime import UTC

import pytest

from routeopt.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("s3cret-pass")
    assert hashed != "s3cret-pass"
    assert verify_password("s3cret-pass", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip() -> None:
    claims = {"sub": "u1", "company_id": "c1", "role": "admin"}
    token = create_access_token(claims)
    decoded = decode_token(token)
    assert decoded["sub"] == "u1"
    assert decoded["company_id"] == "c1"
    assert decoded["role"] == "admin"
    assert decoded["type"] == "access"


def test_refresh_token_typed() -> None:
    token = create_refresh_token({"sub": "u1", "company_id": "c1", "role": "admin"})
    assert decode_token(token)["type"] == "refresh"


def test_hash_token_is_deterministic_and_opaque() -> None:
    token = create_refresh_token({"sub": "u1", "company_id": "c1", "role": "driver"})
    assert hash_token(token) == hash_token(token)
    assert token not in hash_token(token)
    assert len(hash_token(token)) == 64  # sha256 hex


def test_expired_token_rejected() -> None:
    # Craft a token that expired in the past.
    from datetime import datetime, timedelta

    import jwt

    from routeopt.core import security

    payload = {
        "sub": "u1",
        "type": "access",
        "exp": datetime.now(UTC) - timedelta(seconds=1),
    }
    private = security._read_key(security.settings.jwt_private_key_path)
    token = jwt.encode(payload, private, algorithm=security.settings.jwt_algorithm)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)
