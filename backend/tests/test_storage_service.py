"""T-010 (INF-02): object storage service + presigned round-trip."""
from __future__ import annotations

import io
import urllib.request

import pytest

from app.services.storage_service import StorageService, content_type_for


class FakeMinio:
    """Minimal in-memory stand-in mirroring the minio client surface."""

    def __init__(self):
        self.objects: dict[tuple[str, str], bytes] = {}
        self.buckets: set[str] = set()

    def bucket_exists(self, bucket):
        return bucket in self.buckets

    def make_bucket(self, bucket):
        self.buckets.add(bucket)

    def put_object(self, bucket, key, stream, length, content_type=None):
        self.objects[(bucket, key)] = stream.read()

    def fput_object(self, bucket, key, path, content_type=None):
        self.objects[(bucket, key)] = open(path, "rb").read()

    def get_object(self, bucket, key):
        data = self.objects[(bucket, key)]

        class R:
            def read(self):
                return data

            def close(self):
                pass

            def release_conn(self):
                pass

        return R()

    def presigned_get_object(self, bucket, key, expires=None):
        return f"http://fake-minio/{bucket}/{key}?sig=x"

    def remove_object(self, bucket, key):
        del self.objects[(bucket, key)]


@pytest.fixture
def svc():
    return StorageService(backend="minio", bucket="test-bucket", client=FakeMinio())


class TestStorageService:
    def test_local_mode_is_inert(self):
        local = StorageService(backend="local")
        assert not local.enabled
        assert local.store_bytes("uploads/x.pdf", b"data") is None
        assert local.presigned_url("uploads/x.pdf") is None
        assert local.fetch_bytes("uploads/x.pdf") is None
        assert local.delete("uploads/x.pdf") is False

    def test_store_fetch_roundtrip(self, svc):
        key = svc.object_key("uploads", "abc.pdf")
        assert svc.store_bytes(key, b"pdf-bytes", "application/pdf") == key
        assert svc.fetch_bytes(key) == b"pdf-bytes"

    def test_store_file_mirrors_without_moving(self, svc, tmp_path):
        f = tmp_path / "report.xlsx"
        f.write_bytes(b"xlsx-bytes")
        key = svc.object_key("outputs", "T1", f.name)
        assert svc.store_file(key, f) == key
        assert f.exists()  # local copy untouched (mirror-write)
        assert svc.fetch_bytes(key) == b"xlsx-bytes"

    def test_presign_and_delete(self, svc):
        key = svc.object_key("outputs", "r.docx")
        svc.store_bytes(key, b"x")
        assert "test-bucket" in svc.presigned_url(key)
        assert svc.delete(key) is True
        assert svc.fetch_bytes(key) is None

    def test_object_key_layout(self):
        assert StorageService.object_key("uploads", "t1", "a.pdf") == "uploads/t1/a.pdf"
        assert StorageService.object_key("outputs", "b\\c.xlsx") == "outputs/b/c.xlsx"
        with pytest.raises(ValueError):
            StorageService.object_key("random", "x")

    def test_errors_degrade_to_none_not_raise(self):
        class Broken:
            def bucket_exists(self, b):
                raise ConnectionError("minio down")

        svc = StorageService(backend="minio", client=Broken())
        assert svc.store_bytes("uploads/x", b"d") is None
        assert svc.fetch_bytes("uploads/x") is None

    @pytest.mark.asyncio
    async def test_async_wrappers(self, svc):
        key = svc.object_key("uploads", "async.pdf")
        assert await svc.astore_bytes(key, b"a") == key
        assert "test-bucket" in await svc.apresigned_url(key)

    def test_content_types(self):
        assert content_type_for("a.pdf") == "application/pdf"
        assert content_type_for("b.XLSX").endswith("sheet")
        assert content_type_for("c.unknown") == "application/octet-stream"


class TestPresignedRoundTripLiveS3:
    """Acceptance: store → presign → fetch over real S3 HTTP (moto server).

    Stand-in for compose MinIO (Docker unavailable on this machine); the same
    client + S3 API path is exercised. Skips cleanly if moto is absent.
    """

    @pytest.fixture(scope="class")
    def live_svc(self):
        moto_server = pytest.importorskip("moto.server")
        server = moto_server.ThreadedMotoServer(ip_address="127.0.0.1", port=0)
        server.start()
        _host, port = server.get_host_and_port()
        svc = StorageService(
            backend="minio", endpoint=f"127.0.0.1:{port}",
            access_key="testing", secret_key="testing", secure=False,
            bucket="procurementflow-tenders",
        )
        yield svc
        server.stop()

    def test_worker_written_artifact_downloadable_via_presigned_url(self, live_svc, tmp_path):
        # 1. "Worker" writes a report locally, mirrors it to the object store
        report = tmp_path / "BOQ_Analysis_T42.xlsx"
        report.write_bytes(b"worker-generated-report-bytes")
        key = live_svc.object_key("outputs", "T42", report.name)
        assert live_svc.store_file(key, report, content_type_for(report.name)) == key

        # 2. "API replica" (no local file) presigns and the client fetches over HTTP
        url = live_svc.presigned_url(key)
        assert url and "outputs/T42" in url
        fetched = urllib.request.urlopen(url, timeout=10).read()
        assert fetched == b"worker-generated-report-bytes"

    def test_upload_bucket_layout(self, live_svc):
        key = live_svc.object_key("uploads", "deadbeef.pdf")
        assert live_svc.store_bytes(key, b"%PDF-1.4", "application/pdf") == key
        assert live_svc.fetch_bytes(key) == b"%PDF-1.4"
