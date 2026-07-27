from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.security import create_token
from app.main import app


def test_boq_upload_requires_authentication():
    with TestClient(app) as client:
        response = client.post(
            "/api/boq/upload",
            files={"file": ("items.txt", b"1 earth work cum 10", "text/plain")},
            data={"file_type": "boq"},
        )
    assert response.status_code == 401


def test_boq_upload_rejects_unsupported_extension_with_auth():
    token = create_token("boq-test-user", "enterprise")
    with TestClient(app) as client:
        response = client.post(
            "/api/boq/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("items.exe", b"not a boq", "application/octet-stream")},
            data={"file_type": "boq"},
        )
    # T-006 (SEC-05): disallowed types are rejected 415 with a uniform body
    assert response.status_code == 415
    assert "Unsupported file type" in response.json()["detail"]
