"""Live MinIO contract exercised by the isolated production-gate runner."""

from app.services.storage_service import StorageService


def test_minio_store_fetch_delete_roundtrip():
    service = StorageService()
    assert service.enabled
    key = service.object_key("uploads", "production-gate", "probe.txt")
    assert service.store_bytes(key, b"procureflow-minio-probe", "text/plain") == key
    assert service.fetch_bytes(key) == b"procureflow-minio-probe"
    assert service.delete(key) is True
    assert service.fetch_bytes(key) is None
