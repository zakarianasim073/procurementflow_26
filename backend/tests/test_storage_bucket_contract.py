from app.core.config import Settings
from app.services.storage_service import StorageService


def test_canonical_minio_bucket_default(monkeypatch):
    monkeypatch.delenv("MINIO_BUCKET", raising=False)
    monkeypatch.delenv("S3_BUCKET", raising=False)

    assert StorageService().bucket == "procurementflow-tenders"
    assert Settings().S3_BUCKET == "procurementflow-tenders"


def test_minio_bucket_override_is_shared(monkeypatch):
    monkeypatch.setenv("MINIO_BUCKET", "tenant-artifacts")
    monkeypatch.delenv("S3_BUCKET", raising=False)

    assert StorageService().bucket == "tenant-artifacts"
    assert Settings().S3_BUCKET == "tenant-artifacts"
