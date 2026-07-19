"""Shared test fixtures.

Generates an ephemeral RS256 keypair so JWT tests run without any external
setup, and points the app's security module at it.
"""

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from routeopt.core import security


@pytest.fixture(autouse=True)
def jwt_keys(tmp_path, monkeypatch):
    """Write a throwaway RSA keypair and wire security.settings to it."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    priv = tmp_path / "jwt-private.pem"
    pub = tmp_path / "jwt-public.pem"
    priv.write_bytes(private_pem)
    pub.write_bytes(public_pem)

    monkeypatch.setattr(security.settings, "jwt_private_key_path", str(priv))
    monkeypatch.setattr(security.settings, "jwt_public_key_path", str(pub))
    security._read_key.cache_clear()
    yield
    security._read_key.cache_clear()
