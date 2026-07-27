"""T-006 (SEC-05): upload validation hardening acceptance tests."""

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.core.safe_extract import UnsafeZipError, safe_extract_zip


# ── Safe ZIP extraction ─────────────────────────────────────────────────


def _make_zip(path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in members.items():
            zf.writestr(name, data)


class TestSafeExtractZip:
    def test_happy_path_extracts_files(self, tmp_path):
        zp = tmp_path / "ok.zip"
        _make_zip(zp, {
            "Section6_Bill of Quantities (BOQ)/boq.pdf": b"pdf-bytes",
            "Section1_Instructions/itt.pdf": b"more-bytes",
        })
        out = tmp_path / "out"
        extracted = safe_extract_zip(zp, out)
        assert len(extracted) == 2
        assert all(p.is_file() for p in extracted)
        assert (out / "Section6_Bill of Quantities (BOQ)" / "boq.pdf").read_bytes() == b"pdf-bytes"

    def test_path_traversal_member_rejected(self, tmp_path):
        zp = tmp_path / "evil.zip"
        _make_zip(zp, {"../outside.txt": b"escape"})
        out = tmp_path / "out"
        with pytest.raises(UnsafeZipError, match="traversal"):
            safe_extract_zip(zp, out)
        assert not (tmp_path / "outside.txt").exists()

    def test_absolute_path_member_rejected(self, tmp_path):
        zp = tmp_path / "abs.zip"
        with zipfile.ZipFile(zp, "w") as zf:
            zf.writestr("C:/Windows/evil.txt", b"x")
        with pytest.raises(UnsafeZipError):
            safe_extract_zip(zp, tmp_path / "out")

    def test_zip_bomb_ratio_rejected(self, tmp_path):
        zp = tmp_path / "bomb.zip"
        # 50 MB of zeros compresses to a few KB — ratio far above any cap
        _make_zip(zp, {"zeros.bin": b"\x00" * (50 * 1024 * 1024)})
        with pytest.raises(UnsafeZipError, match="ratio"):
            safe_extract_zip(zp, tmp_path / "out", max_ratio=200)

    def test_member_flood_rejected(self, tmp_path):
        zp = tmp_path / "flood.zip"
        _make_zip(zp, {f"f{i}.txt": b"x" for i in range(50)})
        with pytest.raises(UnsafeZipError, match="members"):
            safe_extract_zip(zp, tmp_path / "out", max_members=10)

    def test_total_uncompressed_cap_rejected(self, tmp_path):
        zp = tmp_path / "big.zip"
        _make_zip(zp, {"a.bin": b"a" * 2048, "b.bin": b"b" * 2048})
        with pytest.raises(UnsafeZipError, match="uncompressed"):
            safe_extract_zip(zp, tmp_path / "out", max_total_uncompressed=1024)

    def test_nothing_extracted_when_any_member_unsafe(self, tmp_path):
        zp = tmp_path / "mixed.zip"
        _make_zip(zp, {"good.txt": b"fine", "../bad.txt": b"escape"})
        out = tmp_path / "out"
        with pytest.raises(UnsafeZipError):
            safe_extract_zip(zp, out)
        assert not (out / "good.txt").exists()


# ── API upload rejection (middleware + endpoint) ────────────────────────

@pytest.fixture(scope="module")
def auth_headers():
    from app.core.security import create_token
    token = create_token("upload-security-test", role="owner")
    return {"Authorization": f"Bearer {token}"}


class TestUploadEndpointRejection:
    def test_oversized_upload_rejected_413(self, client, monkeypatch, auth_headers):
        import app.core.upload_validation as uv
        monkeypatch.setattr(uv, "MAX_FILE_SIZE", 1024)  # 1 KB cap for the test

        resp = client.post(
            "/api/boq/upload",
            files={"file": ("big.pdf", io.BytesIO(b"x" * 4096), "application/pdf")},
            headers=auth_headers,
        )
        assert resp.status_code == 413
        body = resp.json()
        assert body["detail"] == "File too large"
        assert body["errors"]

    def test_disallowed_type_rejected_415(self, client, auth_headers):
        resp = client.post(
            "/api/boq/upload",
            files={"file": ("malware.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream")},
            headers=auth_headers,
        )
        assert resp.status_code == 415
        body = resp.json()
        assert body["detail"] == "Unsupported file type"
        assert body["errors"]

    def test_missing_extension_rejected_415(self, client, auth_headers):
        resp = client.post(
            "/api/boq/upload",
            files={"file": ("noext", io.BytesIO(b"data"), "application/octet-stream")},
            headers=auth_headers,
        )
        assert resp.status_code == 415

    def test_content_length_precheck_rejects_413(self, client, monkeypatch, auth_headers):
        import app.core.upload_validation as uv
        monkeypatch.setattr(uv, "MAX_FILE_SIZE", 1024)

        # Content-Length far above cap + overhead → rejected before form parse
        resp = client.post(
            "/api/boq/upload",
            content=b"irrelevant",
            headers={
                **auth_headers,
                "content-type": "multipart/form-data; boundary=x",
                "content-length": str(10 * 1024 * 1024),
            },
        )
        assert resp.status_code == 413

    def test_valid_upload_still_accepted(self, client, auth_headers):
        resp = client.post(
            "/api/boq/upload",
            files={"file": ("boq.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
