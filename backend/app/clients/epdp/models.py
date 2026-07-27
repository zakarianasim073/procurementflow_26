"""Typed response models for the EPDP Data Platform API.

Kept in sync with Enterprise_OS/contracts/API/openapi.json.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Aggregated /v1/health response."""

    status: str
    components: dict[str, Any]


class KnowledgeHealthResponse(BaseModel):
    """/v1/knowledge/health response."""

    status: str
    version: str


class TenderHealthResponse(BaseModel):
    """/v1/tender/health response."""

    status: str
    routes: list[str]


class EvidencePayload(BaseModel):
    """POST /v1/knowledge/evidence request body (Constitution §14 write path)."""

    claim: str
    source_type: str
    source_reference: str
    excerpt: str | None = None
    confidence: float = 1.0
    clause_number: str | None = None
    # X-005 chain fields (additive)
    workspace_id: str | None = None
    decision_ref: str | None = None


class ShortlistFirmResult(BaseModel):
    """One firm's daily shortlist from POST /v1/tender/shortlist."""

    firm_id: str
    generated_at: str
    total_considered: int
    entries: list[dict[str, Any]]


class EvidenceStoreResponse(BaseModel):
    """POST /v1/knowledge/evidence response."""

    stored: bool
    tenant_id: str | None = None
    evidence: dict[str, Any]
