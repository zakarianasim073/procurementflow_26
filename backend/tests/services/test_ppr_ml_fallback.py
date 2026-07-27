"""W-008 (ADR-015): PPR win-probability predict falls back to the heuristic
when no trained model is registered, and never calls fit() in the request path.

These tests run WITHOUT a database — PPRMLService(db=None) routes predict()
straight to the rule-engine fallback because no context features can be built
and no model is registered in the (temp) registry.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.ppr_ml_service import PPRMLService, PPRModelRegistry


@pytest.fixture
def svc(tmp_path: Path):
    svc = PPRMLService(db=None)
    # Isolate from any real trained model on disk.
    svc.registry = PPRModelRegistry(base_dir=tmp_path)
    svc.artifact_path = tmp_path / "ppr_model_bundle.json"
    svc.summary_path = tmp_path / "ppr_model_summary.json"
    return svc


async def test_predict_without_model_returns_heuristic_fallback(svc):
    result = await svc.predict_market_row({"agency": "BWDB", "zone": "A", "estimated_cost": 5000000})
    assert isinstance(result, dict)
    # No trained model registered -> heuristic fallback (no "trained": True).
    assert result.get("trained") is not True
    assert "win" in result and "slt" in result
    assert "probability" in result["win"]


async def test_predict_market_row_is_request_path_only(svc, monkeypatch):
    # Guard: the request path must not (re)train. Monkeypatch train entry points
    # and assert none are invoked while serving a prediction.
    calls = {"train_models": 0, "train_model": 0}

    async def fake_train_models(*a, **k):
        calls["train_models"] += 1
        return {}

    async def fake_train_model(*a, **k):
        calls["train_model"] += 1
        return {}

    monkeypatch.setattr(svc, "train_models", fake_train_models)
    monkeypatch.setattr(svc, "train_model", fake_train_model)

    # Even with a registry miss, predict must serve the heuristic, not train.
    await svc.predict_market_row({"agency": "PWD", "zone": "C"})
    assert calls["train_models"] == 0
    assert calls["train_model"] == 0
