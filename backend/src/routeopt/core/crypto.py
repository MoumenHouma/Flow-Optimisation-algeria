"""Symmetric at-rest encryption for recoverable secrets (e.g. webhook signing keys).

Fernet key is derived deterministically from ``settings.secret_key`` so the same
deployment can decrypt what it wrote. API keys and passwords are hashed instead
(irreversible); this is only for values that must be recovered to be used.
"""

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet

from routeopt.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    digest = hashlib.sha256(get_settings().secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()
