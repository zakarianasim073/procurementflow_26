"""Object storage service — MinIO adoption (INF-02 / T-010).

Single seam for artifact IO. Two backends:

- ``local``  (default): no-op object store; artifacts stay on local disk exactly
  as before. This is the rollback path — flipping STORAGE_BACKEND back to
  ``local`` restores prior behavior without code changes.
- ``minio``: artifacts are mirrored into the MinIO bucket (MINIO_BUCKET) under
  the documented layout ``uploads/...`` and ``outputs/...``; downloads are
  served via presigned URLs.

During transition, local copies are always kept (mirror-write) so existing
local-path readers keep working; the resolver prefers the object store and
falls back to local paths for legacy artifacts.

The minio client is synchronous — async callers must use the ``a*`` wrappers
(asyncio.to_thread) per ADR-004/010.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_PRESIGN_EXPIRY_S = int(os.getenv("STORAGE_PRESIGN_EXPIRY_S", "3600"))

# Documented bucket layout (ARCHITECTURE_BASELINE §7)
CATEGORIES = ("uploads", "outputs", "templates", "embeddings", "exports")


class StorageService:
    """put/get/presign/delete against MinIO, or inert in local mode."""

    def __init__(
        self,
        backend: Optional[str] = None,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        secure: Optional[bool] = None,
        bucket: Optional[str] = None,
        client=None,
    ):
        self.backend = (backend or os.getenv("STORAGE_BACKEND", "local")).strip().lower()
        self.endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.bucket = bucket or os.getenv("MINIO_BUCKET", "procurementflow-tenders")
        environment = os.getenv("ENVIRONMENT", "development").strip().lower()
        development = environment in {"development", "dev", "local", "test"}
        self._access_key = access_key or os.getenv("MINIO_ACCESS_KEY", "") or (
            "procurementflow" if development else ""
        )
        self._secret_key = secret_key or os.getenv("MINIO_SECRET_KEY", "") or (
            "procurementflow123" if development else ""
        )
        self._secure = secure if secure is not None else os.getenv("MINIO_SECURE", "false").strip().lower() == "true"
        self._client = client  # injectable for tests
        self._bucket_checked = False

    @property
    def enabled(self) -> bool:
        return self.backend == "minio"

    def _get_client(self):
        if self._client is None:
            if not self._access_key or not self._secret_key:
                raise RuntimeError("MINIO_ACCESS_KEY and MINIO_SECRET_KEY are required")
            from minio import Minio
            self._client = Minio(
                self.endpoint,
                access_key=self._access_key,
                secret_key=self._secret_key,
                secure=self._secure,
            )
        return self._client

    def _ensure_bucket(self) -> None:
        if self._bucket_checked:
            return
        client = self._get_client()
        if not client.bucket_exists(self.bucket):
            client.make_bucket(self.bucket)
        self._bucket_checked = True

    @staticmethod
    def object_key(category: str, *parts: str) -> str:
        """Build ``category/part1/part2`` keys per the documented layout."""
        if category not in CATEGORIES:
            raise ValueError(f"unknown storage category: {category!r}")
        clean = [str(p).replace("\\", "/").strip("/") for p in parts if p]
        return "/".join([category, *clean])

    # ── Core operations (sync; wrap with a* variants in async paths) ──────

    def store_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> Optional[str]:
        """Store bytes; returns the object key, or None in local mode."""
        if not self.enabled:
            return None
        import io
        try:
            self._ensure_bucket()
            self._get_client().put_object(
                self.bucket, key, io.BytesIO(data), length=len(data), content_type=content_type
            )
            logger.info("Stored object %s/%s (%d bytes)", self.bucket, key, len(data))
            return key
        except Exception as exc:
            logger.warning("Object store put failed for %s: %s", key, exc)
            return None

    def store_file(self, key: str, local_path: Path | str, content_type: str = "application/octet-stream") -> Optional[str]:
        """Mirror a local file into the object store; local file is untouched."""
        if not self.enabled:
            return None
        try:
            self._ensure_bucket()
            self._get_client().fput_object(self.bucket, key, str(local_path), content_type=content_type)
            logger.info("Mirrored %s -> %s/%s", local_path, self.bucket, key)
            return key
        except Exception as exc:
            logger.warning("Object store mirror failed for %s: %s", key, exc)
            return None

    def fetch_bytes(self, key: str) -> Optional[bytes]:
        if not self.enabled:
            return None
        response = None
        try:
            response = self._get_client().get_object(self.bucket, key)
            return response.read()
        except Exception as exc:
            logger.warning("Object store get failed for %s: %s", key, exc)
            return None
        finally:
            if response is not None:
                response.close()
                response.release_conn()

    def presigned_url(self, key: str, expires_s: int = _PRESIGN_EXPIRY_S) -> Optional[str]:
        if not self.enabled or not key:
            return None
        try:
            return self._get_client().presigned_get_object(
                self.bucket, key, expires=timedelta(seconds=expires_s)
            )
        except Exception as exc:
            logger.warning("Presign failed for %s: %s", key, exc)
            return None

    def delete(self, key: str) -> bool:
        if not self.enabled:
            return False
        try:
            self._get_client().remove_object(self.bucket, key)
            return True
        except Exception as exc:
            logger.warning("Object store delete failed for %s: %s", key, exc)
            return False

    # ── Async wrappers (ADR-004/010: no blocking IO in async paths) ───────

    async def astore_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> Optional[str]:
        return await asyncio.to_thread(self.store_bytes, key, data, content_type)

    async def astore_file(self, key: str, local_path: Path | str, content_type: str = "application/octet-stream") -> Optional[str]:
        return await asyncio.to_thread(self.store_file, key, local_path, content_type)

    async def apresigned_url(self, key: str, expires_s: int = _PRESIGN_EXPIRY_S) -> Optional[str]:
        return await asyncio.to_thread(self.presigned_url, key, expires_s)


CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".zip": "application/zip",
    ".txt": "text/plain",
    ".json": "application/json",
    ".csv": "text/csv",
}


def content_type_for(filename: str) -> str:
    return CONTENT_TYPES.get(Path(filename).suffix.lower(), "application/octet-stream")


storage_service = StorageService()
