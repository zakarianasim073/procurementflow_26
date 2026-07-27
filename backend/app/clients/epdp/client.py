"""HTTP client for the EPDP Data Platform API (house style: EPDP backend/clients/epdp)."""

from __future__ import annotations

from typing import Any

import httpx

from app.clients.epdp.config import EPDPClientConfig
from app.clients.epdp.errors import (
    EPDPAuthError,
    EPDPClientError,
    EPDPConnectionError,
    EPDPError,
    EPDPNotFoundError,
    EPDPValidationError,
)
from app.clients.epdp.models import (
    EvidencePayload,
    EvidenceStoreResponse,
    HealthResponse,
    KnowledgeHealthResponse,
    ShortlistFirmResult,
    TenderHealthResponse,
)


def _build_error(response: httpx.Response) -> EPDPError:
    status = response.status_code
    if status in (401, 403):
        return EPDPAuthError(response.text)
    if status == 404:
        return EPDPNotFoundError(response.text)
    if status == 422:
        return EPDPValidationError(response.text)
    return EPDPClientError(f"HTTP {status}: {response.text}")


class EPDPClient:
    """Typed HTTP client for the ProcureFlow Data Platform /v1 API."""

    def __init__(
        self,
        config: EPDPClientConfig | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._config = config or EPDPClientConfig()
        self._client = httpx.AsyncClient(
            base_url=self._config.base_url,
            timeout=httpx.Timeout(self._config.timeout),
            verify=self._config.verify_ssl,
            transport=transport,
            headers={
                "X-API-Key": self._config.api_key,
                "X-Tenant-ID": self._config.tenant_id,
            },
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise EPDPConnectionError(f"Request timed out: {exc}") from exc
        except httpx.TransportError as exc:
            raise EPDPConnectionError(f"Transport error: {exc}") from exc

        if response.is_error:
            raise _build_error(response)

        return response.json()

    # ── Health ──────────────────────────────────────────────────────

    async def health(self) -> HealthResponse:
        """GET /v1/health — aggregated module health."""
        data = await self._request("GET", "/v1/health")
        return HealthResponse(**data)

    async def knowledge_health(self) -> KnowledgeHealthResponse:
        """GET /v1/knowledge/health — knowledge module health."""
        data = await self._request("GET", "/v1/knowledge/health")
        return KnowledgeHealthResponse(**data)

    async def tender_health(self) -> TenderHealthResponse:
        """GET /v1/tender/health — tender module health."""
        data = await self._request("GET", "/v1/tender/health")
        return TenderHealthResponse(**data)

    # ── Shortlist (W-003 wiring) ────────────────────────────────────

    async def shortlist(
        self,
        profiles: list[dict[str, Any]],
        opportunities: list[dict[str, Any]] | None = None,
        now: str | None = None,
    ) -> list[ShortlistFirmResult]:
        """POST /v1/tender/shortlist — per-firm daily shortlist (filtering only)."""
        body: dict[str, Any] = {"profiles": profiles}
        if opportunities is not None:
            body["opportunities"] = opportunities
        if now is not None:
            body["now"] = now
        data = await self._request("POST", "/v1/tender/shortlist", json=body)
        return [ShortlistFirmResult(**row) for row in data]

    # ── Evidence (the only write path — core/03 L5) ─────────────────

    async def post_evidence(self, payload: EvidencePayload) -> EvidenceStoreResponse:
        """POST /v1/knowledge/evidence — persist an AI evidence item to P03."""
        data = await self._request(
            "POST", "/v1/knowledge/evidence", json=payload.model_dump(mode="json")
        )
        return EvidenceStoreResponse(**data)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> EPDPClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
