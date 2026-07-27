from pathlib import Path

import pytest

from app.services.file_upload_service import FileUploadService
from app.services.tender_manager import TenderManager
from app.services.webhook_service import _validate_webhook_url
from app.services.storage_service import StorageService
from app.core.distributed_lock import DistributedLock


def test_document_lookup_rejects_path_outside_upload_root(tmp_path, monkeypatch):
    base = tmp_path / "base"
    upload_root = base / "uploads" / "documents"
    upload_root.mkdir(parents=True)
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")
    monkeypatch.setattr(FileUploadService, "UPLOAD_DIR", upload_root)
    monkeypatch.setattr("app.services.file_upload_service.settings.BASE_DIR", str(base))

    assert FileUploadService.get_file_path(str(outside)) is None


def test_tender_manager_rejects_prefix_sibling_escape(tmp_path):
    manager = TenderManager(str(tmp_path / "tenders"))

    with pytest.raises(ValueError):
        manager._tender_dir("../tenders-escaped")


@pytest.mark.asyncio
async def test_webhook_rejects_loopback_destination():
    with pytest.raises(ValueError, match="non-public"):
        await _validate_webhook_url("http://127.0.0.1/internal")


@pytest.mark.asyncio
async def test_distributed_lock_denies_acquisition_without_redis(monkeypatch):
    lock_manager = DistributedLock()

    async def no_clients():
        return []

    monkeypatch.setattr(lock_manager, "_get_clients", no_clients)
    assert await lock_manager.acquire("critical-job") is None


def test_production_minio_requires_explicit_credentials(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("MINIO_ACCESS_KEY", raising=False)
    monkeypatch.delenv("MINIO_SECRET_KEY", raising=False)
    service = StorageService(backend="minio")

    with pytest.raises(RuntimeError, match="MINIO_ACCESS_KEY"):
        service._get_client()
