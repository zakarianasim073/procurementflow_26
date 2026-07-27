"""W-008 (ADR-015): a pre-trained model loaded from the registry produces the
same prediction as the in-memory model (deterministic round-trip), and
predict() serves it from the registry without re-fitting.

Runs WITHOUT a database — context features are injected via monkeypatch so the
ML inference path is exercised directly.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.services.ppr_ml_service import (
    PPRMLService,
    PPRModelRegistry,
    PortableBoostingModel,
    get_regime,
)

FEATURES = np.array(
    [
        [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
        [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3],
        [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
        [0.2, 0.4, 0.6, 0.8, 0.1, 0.3, 0.5, 0.7, 0.9, 0.2, 0.4, 0.6, 0.8, 0.1, 0.3, 0.5, 0.7],
    ]
)
WIN_Y = np.array([1, 0, 1, 0])


async def _coro(value):
    return value


def _trained_model():
    m = PortableBoostingModel(PPRMLService.FEATURE_NAMES, PPRMLService.WIN_MONOTONIC)
    m.fit(FEATURES, WIN_Y)
    return m


def _bundle_for(model: PortableBoostingModel) -> dict:
    return {
        "trained_at": "2026-01-01T00:00:00+00:00",
        "feature_names": PPRMLService.FEATURE_NAMES,
        "models": {"slt": model.to_dict(), "win": model.to_dict()},
        "dataset": {"rows": 4},
        "metrics": {"win": {"roc_auc": 0.9}},
        "summary": {"trained": True, "rows": 4},
    }


@pytest.fixture
def svc_with_registry(tmp_path: Path, monkeypatch):
    svc = PPRMLService(db=None)
    svc.registry = PPRModelRegistry(base_dir=tmp_path)
    svc.artifact_path = tmp_path / "ppr_model_bundle.json"
    model = _trained_model()
    svc.registry.save("BWDB_A_PPR2025", _bundle_for(model), {"rows": 4})

    # Inject features so the ML inference path runs without a DB.
    async def fake_context_features(payload, db=None):
        return list(FEATURES[0]), {
            "evidence_score": 0.3,
            "bidder_count": 3,
            "bid_ratio": 1.0,
            "discount_pct": 0.0,
            "contractor_history_rows": 1,
            "regime": "PPR2025",
        }

    monkeypatch.setattr(svc, "_context_features", fake_context_features)
    monkeypatch.setattr(svc, "_build_explanation", lambda *a, **k: _coro({"available": False}))
    return svc, model


async def test_registry_prediction_matches_in_memory_model(svc_with_registry):
    svc, model = svc_with_registry
    payload = {"agency": "BWDB", "zone": "A", "tender_open_date": "2026-03-01"}
    assert get_regime(payload["tender_open_date"]) == "PPR2025"

    result = await svc.predict(payload)
    assert result.get("trained") is True

    # The model served from the registry must be byte-for-byte (JSON) faithful
    # to the in-memory model: reconstruct it and predict with the service's own
    # blend so we compare like-for-like.
    reg = svc.registry.get_latest("BWDB_A_PPR2025")
    recon = PortableBoostingModel.from_dict(reg[0]["models"]["win"])
    raw = float(recon.predict_proba(FEATURES[0].reshape(1, -1))[0])
    ctx = {
        "evidence_score": 0.3,
        "bidder_count": 3,
        "bid_ratio": 1.0,
        "discount_pct": 0.0,
        "contractor_history_rows": 1,
        "regime": "PPR2025",
    }
    expected_win = round(svc._blend_sparse_history_probabilities(raw, raw, ctx)[1], 4)
    assert abs(result["win"]["probability"] - expected_win) < 1e-9


async def test_registry_falls_back_to_global_all_model(tmp_path: Path, monkeypatch):
    svc = PPRMLService(db=None)
    svc.registry = PPRModelRegistry(base_dir=tmp_path)
    svc.artifact_path = tmp_path / "ppr_model_bundle.json"
    model = _trained_model()
    # Only the global "all" model is registered; the scoped key is absent.
    svc.registry.save("all", _bundle_for(model), {"rows": 4})

    async def fake_context_features(payload, db=None):
        return list(FEATURES[1]), {
            "evidence_score": 0.2,
            "bidder_count": 2,
            "bid_ratio": 1.0,
            "discount_pct": 0.0,
            "contractor_history_rows": 1,
            "regime": "PPR2025",
        }

    monkeypatch.setattr(svc, "_context_features", fake_context_features)
    monkeypatch.setattr(svc, "_build_explanation", lambda *a, **k: _coro({"available": False}))

    payload = {"agency": "PWD", "zone": "D", "tender_open_date": "2026-04-01"}
    result = await svc.predict(payload)
    assert result.get("trained") is True

    reg = svc.registry.get_latest("all")
    recon = PortableBoostingModel.from_dict(reg[0]["models"]["win"])
    raw = float(recon.predict_proba(FEATURES[1].reshape(1, -1))[0])
    ctx = {
        "evidence_score": 0.2,
        "bidder_count": 2,
        "bid_ratio": 1.0,
        "discount_pct": 0.0,
        "contractor_history_rows": 1,
        "regime": "PPR2025",
    }
    expected_win = round(svc._blend_sparse_history_probabilities(raw, raw, ctx)[1], 4)
    assert abs(result["win"]["probability"] - expected_win) < 1e-9
