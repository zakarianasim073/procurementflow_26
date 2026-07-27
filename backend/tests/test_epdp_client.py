"""W-005 acceptance (ProcureFlow side): ProcureFlow calls EPDP /v1 via the typed client in CI.

Transport is mocked (httpx.MockTransport) so CI needs no live EPDP server;
path conformance is checked against the published contract artifact.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from app.clients.epdp import (
    EPDPAuthError,
    EPDPClient,
    EPDPClientConfig,
    EPDPConnectionError,
    EPDPNotFoundError,
    EPDPValidationError,
)

CONTRACT = (
    Path(__file__).resolve().parents[3]
    / "Procureflow_Enterprise_OS"
    / "contracts"
    / "API"
    / "openapi.json"
)

CONFIG = EPDPClientConfig(base_url="http://epdp.test", api_key="test-key", tenant_id="tenant-9")

RESPONSES = {
    "/v1/health": {"status": "ok", "components": {"knowledge": "ok", "tender": "ok"}},
    "/v1/knowledge/health": {"status": "ok", "version": "1.0.0"},
    "/v1/tender/health": {"status": "ok", "routes": ["opportunities", "workspaces"]},
}


def _transport(status_code: int = 200) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if status_code != 200:
            return httpx.Response(status_code, text="error")
        return httpx.Response(200, json=RESPONSES[request.url.path])

    return httpx.MockTransport(handler), seen


@pytest.mark.asyncio
async def test_health_endpoints_typed_roundtrip():
    transport, seen = _transport()
    async with EPDPClient(CONFIG, transport=transport) as client:
        health = await client.health()
        knowledge = await client.knowledge_health()
        tender = await client.tender_health()

    assert health.status == "ok" and health.components["tender"] == "ok"
    assert knowledge.version == "1.0.0"
    assert tender.routes == ["opportunities", "workspaces"]
    assert [r.url.path for r in seen] == list(RESPONSES)


@pytest.mark.asyncio
async def test_auth_and_tenant_headers_sent_on_every_request():
    transport, seen = _transport()
    async with EPDPClient(CONFIG, transport=transport) as client:
        await client.health()

    request = seen[0]
    assert request.headers["X-API-Key"] == "test-key"
    assert request.headers["X-Tenant-ID"] == "tenant-9"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,exc",
    [(401, EPDPAuthError), (403, EPDPAuthError), (404, EPDPNotFoundError), (422, EPDPValidationError)],
)
async def test_error_mapping(status, exc):
    transport, _ = _transport(status)
    async with EPDPClient(CONFIG, transport=transport) as client:
        with pytest.raises(exc):
            await client.health()


@pytest.mark.asyncio
async def test_transport_failure_maps_to_connection_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    async with EPDPClient(CONFIG, transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(EPDPConnectionError):
            await client.health()


def test_client_paths_exist_in_published_contract():
    if not CONTRACT.exists():
        pytest.skip("contract artifact not present on this machine")
    spec_paths = set(json.loads(CONTRACT.read_text(encoding="utf-8"))["paths"])
    assert set(RESPONSES) <= spec_paths
