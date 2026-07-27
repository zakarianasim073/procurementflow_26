import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core import rate_limiter


@pytest.mark.asyncio
async def test_rate_limit_uses_distributed_tenant_bucket(monkeypatch):
    calls = []

    class FakeDistributedLimiter:
        enabled = True

        async def is_allowed(self, tenant_id, endpoint, plan, per_minute=None):
            calls.append((tenant_id, endpoint, plan, per_minute))
            return False, "limited"

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/search/tenders",
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
    )
    request.state.user = {
        "id": "user-1",
        "tenant_id": "tenant-1",
        "plan": "pro",
    }
    monkeypatch.setattr(
        rate_limiter,
        "get_tenant_rate_limiter",
        lambda: FakeDistributedLimiter(),
    )

    response = await rate_limiter.rate_limit_middleware(
        request,
        lambda request: JSONResponse({"unexpected": True}),
    )

    assert response.status_code == 429
    assert calls == [("tenant-1", "/api/v1/search", "pro", 30)]
