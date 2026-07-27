from contextlib import asynccontextmanager

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core import quota_middleware


@pytest.mark.asyncio
async def test_authenticated_tenant_quota_exhaustion_returns_429(monkeypatch):
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/agents/agent-001/run",
            "headers": [],
        }
    )
    request.state.user = {"id": "viewer-1", "tenant_id": "tenant-1"}
    request.state.tenant_id = "tenant-1"

    @asynccontextmanager
    async def fake_session():
        yield object()

    async def no_quota(db, tenant_id):
        return False, "quota exhausted"

    monkeypatch.setattr(quota_middleware, "get_async_session", fake_session)
    monkeypatch.setattr(
        quota_middleware.QuotaService,
        "check_tender_quota",
        no_quota,
    )

    middleware = quota_middleware.QuotaEnforcementMiddleware(lambda scope, receive, send: None)
    response = await middleware.dispatch(
        request,
        lambda request: JSONResponse({"unexpected": True}),
    )

    assert response.status_code == 429
