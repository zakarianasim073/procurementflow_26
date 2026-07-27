from __future__ import annotations

from app.core.security import create_token, decode_token
from app.services.decision_calibration import decision_calibration_service


def test_jwt_contains_tenant_role_and_scopes():
    token = create_token(
        "user-1",
        "enterprise",
        tenant_id="tenant-a",
        role="manager",
    )
    payload = decode_token(token)
    assert payload["tenant_id"] == "tenant-a"
    assert payload["role"] == "manager"
    assert set(payload["scopes"]) >= {"read", "write", "approve"}


def test_executive_policy_returns_model_metadata_and_features():
    policy = decision_calibration_service.executive_policy({
        "tender_id": "1293482",
        "win_probability": 72,
        "expected_margin": 8,
        "capacity_available": True,
        "degraded_mode": False,
        "evidence_score": 0.8,
        "intel_source_count": 3,
    })
    assert policy["model_version"]
    assert policy["decision"] in {"BID", "NO-BID"}
    assert "feature_snapshot" in policy
    assert "explanation" in policy
