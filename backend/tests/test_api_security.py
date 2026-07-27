from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_token, decode_token
from app.main import app


def test_api_health_is_public(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_protected_api_requires_bearer_token(client):
    response = client.get("/api/competitors/stats")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/dashboard/summary",
        "/api/v1/contractors",
        "/api/v1/leaderboards/execution_score",
        "/api/v1/agencies/performance/BWDB",
        "/api/v1/capacity-risk/health",
        "/api/v1/tender-docs/generate",
        "/api/v1/rate-analysis/summary",
        "/api/v1/government-portal/status",
    ],
)
def test_enterprise_data_routes_are_not_public(path: str, client):
    response = client.get(path)
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("post", "/api/brain/store", {"entry_type": "note", "data": {"x": 1}}),
        ("post", "/api/brain/idle-cycle", {}),
        ("post", "/api/pipeline/run", {"mode": "intelligence"}),
        ("post", "/api/clients/create", {"name": "Demo", "slug": "demo"}),
        ("post", "/api/thoughts/propose", {"title": "Unsafe guest proposal"}),
    ],
)
def test_brain_write_routes_require_dependency_auth_even_without_middleware(method: str, path: str, payload: dict):
    previous = settings.REQUIRE_API_AUTH
    settings.REQUIRE_API_AUTH = False
    try:
        from app.api.brain_router import router as brain_router

        brain_app = FastAPI()
        brain_app.include_router(brain_router)
        response = getattr(TestClient(brain_app), method)(path, json=payload)
        assert response.status_code == 401
        assert response.json()["detail"] == "Authentication required"
    finally:
        settings.REQUIRE_API_AUTH = previous


def test_authenticated_api_request_reaches_router_layer(client):
    token = create_token("security-test-user", "enterprise")
    response = client.get(
        "/api/route-that-does-not-exist",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_jwt_previous_secret_allows_rotation_window():
    previous = list(settings.JWT_PREVIOUS_SECRETS)
    try:
        old_secret = "old-rotation-secret"
        settings.JWT_PREVIOUS_SECRETS = [old_secret]
        token = jwt.encode(
            {
                "sub": "rotated-user",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                "iat": datetime.now(timezone.utc),
                "plan": "enterprise",
            },
            old_secret,
            algorithm=settings.JWT_ALGORITHM,
        )

        payload = decode_token(token)

        assert payload["sub"] == "rotated-user"
    finally:
        settings.JWT_PREVIOUS_SECRETS = previous


def test_jwt_unconfigured_old_secret_is_rejected():
    previous = list(settings.JWT_PREVIOUS_SECRETS)
    try:
        settings.JWT_PREVIOUS_SECRETS = []
        token = jwt.encode(
            {
                "sub": "stale-user",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                "iat": datetime.now(timezone.utc),
                "plan": "enterprise",
            },
            "unconfigured-old-secret",
            algorithm=settings.JWT_ALGORITHM,
        )

        try:
            decode_token(token)
        except jwt.InvalidTokenError:
            pass
        else:
            raise AssertionError("Token signed with an unconfigured secret was accepted")
    finally:
        settings.JWT_PREVIOUS_SECRETS = previous
