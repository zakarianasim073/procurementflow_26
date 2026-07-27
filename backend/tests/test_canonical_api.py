from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core.security import create_token
from app.db.base import get_async_session
from app.main import app


class _MappingResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def one(self):
        return self._rows[0]

    def all(self):
        return self._rows


class _CanonicalStatusSession:
    def __init__(self):
        self.calls = 0

    async def execute(self, query, params=None):
        self.calls += 1
        if self.calls == 1:
            return _MappingResult([{
                "tenders": 10,
                "contracts": 20,
                "contractors": 3,
                "aliases": 4,
                "jv_links": 1,
                "amount_audit_rows": 5,
            }])
        if self.calls == 2:
            return _MappingResult([{
                "trusted_amounts": 12,
                "low_confidence_amounts": 2,
                "missing_or_rejected_amounts": 1,
                "warning_rows": 3,
                "suspicious_huge_amounts": 1,
                "suspicious_tiny_amounts": 2,
                "avg_amount_confidence": 0.86,
            }])
        if self.calls == 3:
            return _MappingResult([{
                "contractors_with_amounts": 3,
                "contractors_with_capacity": 2,
                "joint_venture_contractors": 1,
                "avg_data_confidence": 0.81,
                "last_rebuilt_at": datetime(2026, 7, 5, tzinfo=timezone.utc),
            }])
        return _MappingResult([{
            "canonical_contractor_id": "abc",
            "display_name": "Test Contractor",
            "total_wins": 2,
            "total_award_amount_bdt": 1000.0,
            "last_5yr_awarded_amount_bdt": 1000.0,
            "work_in_hand_bdt": 100.0,
            "estimated_turnover_bdt": 200.0,
            "tender_capacity_bdt": 300.0,
            "data_confidence_score": 0.8,
        }])


async def _override_session():
    yield _CanonicalStatusSession()


def test_canonical_status_requires_owner_or_admin_token():
    with TestClient(app) as client:
        response = client.get("/api/canonical/status")
    assert response.status_code == 401


def test_canonical_status_returns_quality_summary_for_owner():
    token = create_token(
        "owner-test-user",
        "enterprise",
        tenant_id="tenant-owner-zakaria-nasim",
        role="owner",
    )
    app.dependency_overrides[get_async_session] = _override_session
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/canonical/status",
                headers={"Authorization": f"Bearer {token}"},
            )
    finally:
        app.dependency_overrides.pop(get_async_session, None)

    assert response.status_code == 200
    body = response.json()
    assert body["tables"]["contracts"] == 20
    assert body["amount_quality"]["trusted_amounts"] == 12
    assert body["contractor_quality"]["contractors_with_capacity"] == 2
    assert body["top_capacity_contractors"][0]["canonical_contractor_id"] == "abc"
