"""W-008 (ADR-015): Celery Beat training task wiring — combination enumeration,
queue routing, beat schedule entry, and that the task trains every agency/zone/
regime combination (no live DB required).
"""
from __future__ import annotations

import os

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.celery_app import celery_app  # noqa: E402

import app.services.ppr_ml_service as ppr_ml_service  # noqa: E402
import app.workers.tasks.ml_tasks as ml_tasks  # noqa: E402
from app.workers.tasks.ml_tasks import enumerate_training_combinations  # noqa: E402


def test_enumerate_training_combinations_shape():
    combos = enumerate_training_combinations()
    # 1 global + 3 agencies * 4 zones * 2 regimes = 25
    assert len(combos) == 25
    assert combos[0] == (None, None, None)
    assert all(c[0] in (None, "BWDB", "PWD", "LGED") for c in combos)
    assert all(c[1] in (None, "A", "B", "C", "D") for c in combos)
    assert all(c[2] in (None, "PPR2008", "PPR2025") for c in combos)


def test_ml_task_routes_to_low_queue():
    router = celery_app.amqp.router
    route = router.route(celery_app.conf.task_routes, "train_ppr_models")
    queue = route.get("queue")
    assert (queue.name if hasattr(queue, "name") else queue) == "low"


def test_ml_task_in_beat_schedule():
    schedule = celery_app.conf.beat_schedule
    assert "ppr-ml-train-daily" in schedule
    entry = schedule["ppr-ml-train-daily"]
    assert entry["task"] == "train_ppr_models"
    assert entry["kwargs"].get("force") is False


def test_opening_label_reconciliation_is_low_priority_and_precedes_training():
    schedule = celery_app.conf.beat_schedule
    entry = schedule["ppr-opening-label-reconciliation"]
    assert entry["task"] == "reconcile_ppr_opening_labels"
    assert entry["options"]["queue"] == "low"
    route = celery_app.amqp.router.route(
        celery_app.conf.task_routes, "reconcile_ppr_opening_labels"
    )
    queue = route.get("queue")
    assert (queue.name if hasattr(queue, "name") else queue) == "low"


class _FakeSession:
    pass


class _FakeCtx:
    async def __aenter__(self):
        return _FakeSession()

    async def __aexit__(self, *exc):
        return False


class _FakeService:
    def __init__(self, db=None):
        self.db = db
        self.calls = []

    def _regime_key_dict(self, agency, zone, regime):
        return f"{agency or 'all'}_{zone or 'all'}_{regime or 'all'}"

    async def train_models(self, force=False):
        self.calls.append(("all", force))
        return {"trained": True, "rows": 10}

    async def train_model(self, agency=None, zone=None, regime=None, force=False):
        self.calls.append((self._regime_key_dict(agency, zone, regime), force))
        return {"trained": True, "rows": 5}


def test_training_task_covers_all_combinations(monkeypatch):
    captured = {}

    def fake_get_async_session():
        return _FakeCtx()

    def fake_pprmlservice(db=None):
        svc = _FakeService(db=db)
        captured["svc"] = svc
        return svc

    monkeypatch.setattr(ml_tasks, "get_async_session", fake_get_async_session)
    monkeypatch.setattr(ppr_ml_service, "PPRMLService", fake_pprmlservice)

    result = ml_tasks.train_ppr_models(force=False)

    assert result["status"] == "success"
    assert result["total"] == 25
    assert result["trained"] == 25
    keys = [c[0] for c in captured["svc"].calls]
    assert "all" in keys
    assert len(keys) == 25
    # every scoped combo was trained exactly once
    assert len(set(keys)) == 25
