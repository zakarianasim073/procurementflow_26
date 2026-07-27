"""Integration tests for TEN/KNOW workspace API endpoints.

Covers: tender PATCH, SOR, compliance, competitor, submission, awards, tender-docs.
Uses Bearer token auth via create_token for protected v1 endpoints.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def auth_headers():
    from app.core.security import create_token
    token = create_token("test-user-001")
    return {"Authorization": f"Bearer {token}"}


# ── Health endpoints (public) ─────────────────────────────────────────────


class TestHealthEndpoints:
    def test_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json().get("status") in ("healthy", "ok")

    def test_live(self, client):
        r = client.get("/api/live")
        assert r.status_code == 200

    def test_ready(self, client):
        r = client.get("/api/ready")
        assert r.status_code in (200, 503)


# ── SOR endpoints ─────────────────────────────────────────────────────────


class TestSorEndpoints:
    def test_sor_agencies(self, client):
        r = client.get("/api/sor/agencies")
        assert r.status_code == 200
        data = r.json()
        assert "agencies" in data
        names = {a["name"] for a in data["agencies"]}
        assert names & {"BWDB", "PWD", "LGED"}

    def test_sor_lookup(self, client):
        r = client.get("/api/sor/lookup", params={"code": "01.1.1", "agency": "PWD", "zone": "A"})
        assert r.status_code in (200, 404)


# ── Tender PATCH endpoint ─────────────────────────────────────────────────


class TestTenderPatch:
    def test_patch_nonexistent_returns_404(self, client, auth_headers):
        r = client.patch(
            "/api/v1/tender/db/does-not-exist",
            json={"status": "submitted"},
            headers=auth_headers,
        )
        assert r.status_code == 404


# ── Competitor endpoints ──────────────────────────────────────────────────


class TestCompetitorEndpoints:
    def test_competitors_list(self, client, auth_headers):
        r = client.get("/api/v1/competitors", headers=auth_headers)
        assert r.status_code in (200, 404)

    def test_competitor_analysis_no_tender(self, client, auth_headers):
        r = client.get("/api/v1/competitors/analysis/nonexistent", headers=auth_headers)
        assert r.status_code in (200, 404)


# ── Awards endpoints ──────────────────────────────────────────────────────


class TestAwardEndpoints:
    def test_award_stats(self, client, auth_headers):
        r = client.get("/api/v1/awards/stats", headers=auth_headers)
        assert r.status_code in (200, 404)

    def test_award_list(self, client, auth_headers):
        r = client.get("/api/v1/awards?limit=5", headers=auth_headers)
        assert r.status_code in (200, 404)


# ── Tender docs endpoints ─────────────────────────────────────────────────


class TestTenderDocs:
    def test_list_docs_nonexistent(self, client, auth_headers):
        r = client.get("/api/v1/tender-docs/nonexistent/list", headers=auth_headers)
        assert r.status_code in (200, 404)

    def test_generate_requires_body(self, client, auth_headers):
        r = client.post("/api/v1/tender-docs/generate", headers=auth_headers)
        assert r.status_code in (400, 422)


# ── Compliance endpoints ──────────────────────────────────────────────────


class TestComplianceEndpoints:
    def test_compliance_check_nonexistent(self, client, auth_headers):
        r = client.get("/api/v1/validation/tender/nonexistent", headers=auth_headers)
        assert r.status_code in (200, 404)


# ── Submission endpoints ──────────────────────────────────────────────────


class TestSubmissionEndpoints:
    def test_tender_detail_nonexistent(self, client, auth_headers):
        r = client.get("/api/v1/tender/nonexistent", headers=auth_headers)
        assert r.status_code in (200, 404)

    def test_tender_list(self, client, auth_headers):
        r = client.get("/api/v1/tender?limit=5", headers=auth_headers)
        assert r.status_code in (200, 404)
