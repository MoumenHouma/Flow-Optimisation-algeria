"""S3-compatible object storage (MinIO/S3) for proof-of-delivery files.

ARCHITECTURE §2.5: files live in MinIO/S3 (SSE-S3 at rest). Objects are private;
the app stores only the object *key* and mints short-lived presigned GET URLs on
read. boto3 is synchronous, so its blocking calls are offloaded to a thread.

The engine cannot run in the sandbox (like OSRM/Nominatim); tests inject a fake
via the ``get_storage`` FastAPI dependency.
"""

import asyncio
from functools import lru_cache
from typing import Protocol

import boto3
from botocore.client import Config

from routeopt.config import get_settings


class Storage(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...

    async def presigned_get(self, key: str, expires_in: int = 3600) -> str: ...


class S3Storage:
    """Thin async wrapper over a boto3 S3 client (works with MinIO)."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
    ) -> None:
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4"),
        )

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )

    async def presigned_get(self, key: str, expires_in: int = 3600) -> str:
        url: str = await asyncio.to_thread(
            self._client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return url


@lru_cache
def _build_storage() -> S3Storage:
    s = get_settings()
    return S3Storage(s.s3_endpoint, s.s3_access_key, s.s3_secret_key, s.s3_bucket)


def get_storage() -> Storage:
    """FastAPI dependency — override in tests to inject a fake."""
    return _build_storage()
