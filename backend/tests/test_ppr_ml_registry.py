"""ENT-05: ML model registry versioning, rollback, and version recording on prediction."""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

from app.services.ppr_ml_service import PPRMLService, PPRModelRegistry, PortableBoostingModel


def _valid_model_dict(svc: PPRMLService) -> Dict[str, Any]:
    return PortableBoostingModel(
        feature_names=svc.FEATURE_NAMES, monotonic_cst=svc.SLT_MONOTONIC
    ).to_dict()


def test_registry_version_and_rollback():
    """Versioned registry records versions and rollback promotes the prior one."""
    reg = PPRModelRegistry(base_dir=Path(tempfile.mkdtemp()))
    v1 = reg.save("all", {"m": 1}, {"metrics": {"auc": 0.70}})
    assert reg.latest_version("all") == v1

    v2 = reg.save("all", {"m": 2}, {"metrics": {"auc": 0.80}})
    assert reg.latest_version("all") == v2

    # Rollback promotes the previously-live version.
    assert reg.rollback("all") is True
    assert reg.latest_version("all") == v1

    bundle, _ = reg.get_latest("all")
    assert bundle == {"m": 1}

    # No history -> rollback fails gracefully.
    assert reg.rollback("never_trained") is False


def test_predict_records_registry_version():
    """ENT-05 acceptance: every prediction carries the actual registered version id."""
    svc = PPRMLService(db=None)
    svc.registry = PPRModelRegistry(base_dir=Path(tempfile.mkdtemp()))
    model = _valid_model_dict(svc)
    payload = {
        "agency": "BWDB",
        "zone": "A",
        "tender_open_date": "2025-10-01",  # -> PPR2025 regime
        "estimated_cost": 1000,
        "bid_price": 950,
        "bidder_count": 3,
    }
    key = svc._regime_key(payload)
    version = svc.registry.save(
        key, {"models": {"slt": model, "win": model}, "summary": {}}, {"trained": True}
    )

    async def _fake_features(self, p):  # noqa: ANN001
        return (
            list(range(len(svc.FEATURE_NAMES))),
            {
                "evidence_score": 0.7,
                "bid_ratio": 0.95,
                "discount_pct": 5.0,
                "bidder_count": 3,
                "regime": "PPR2025",
                "contractor_history_rows": 5,
            },
        )

    async def _fake_explanation(self, *args, **kwargs):  # noqa: ANN001
        return {"available": False}

    with patch.object(PPRMLService, "_context_features", _fake_features), patch.object(
        PPRMLService, "_build_explanation", _fake_explanation
    ):
        result = asyncio.run(svc.predict(payload))

    assert result["trained"] is True
    assert result["model_version"] == version


def test_predict_fallback_records_rule_version():
    """When no model is registered, prediction records the rule-fallback version."""
    svc = PPRMLService(db=None)
    svc.registry = PPRModelRegistry(base_dir=Path(tempfile.mkdtemp()))
    # Ensure no legacy single-file bundle is found either.
    svc.artifact_path = Path(tempfile.mkdtemp()) / "no_such_bundle.json"
    payload = {"estimated_cost": 1000, "bid_price": 950, "bidder_count": 3}
    result = asyncio.run(svc.predict(payload))
    assert result["trained"] is False
    assert result["model_version"] == "rule-fallback"
