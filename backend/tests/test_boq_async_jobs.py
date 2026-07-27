"""T-013 (API-01): async BOQ comparison offload — 202 submission, job lifecycle,
sync/async parity on the golden fixture, and failure injection."""

from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import settings
from app.core.security import create_token
from app.main import app

FIXTURE_PDF = Path(__file__).parent / "golden" / "fixtures" / "boq_1290886.pdf"
GOLDEN = json.loads((Path(__file__).parent / "golden" / "boq_golden.json").read_text())

# Volatile keys excluded from sync/async parity (timestamps, ids, artifact paths)
_VOLATILE = {
    "comparison_id", "created_at", "excel_path", "docx_path", "tenderai_dir",
    "excel_object_key", "docx_object_key", "excel_url", "docx_url",
}


def _auth() -> dict:
    return {"Authorization": f"Bearer {create_token('boq-async-test-user', 'enterprise')}"}


def _upload_fixture(content: bytes | None = None) -> str:
    fid = f"t013{uuid.uuid4().hex[:6]}"
    dest = Path(settings.BASE_DIR) / "uploads" / f"{fid}.pdf"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if content is None:
        shutil.copyfile(FIXTURE_PDF, dest)
    else:
        dest.write_bytes(content)
    return fid


def _sync_conn():
    from app.db.database import get_sync_engine

    return get_sync_engine().connect()


def _cleanup(fid: str) -> None:
    """Remove rows created for this fixture id (FK order: jobs → comparisons → items → tender)."""
    with _sync_conn() as conn:
        conn.execute(
            text("DELETE FROM boq_jobs WHERE params->>'boq_file_id' = :fid"), {"fid": fid}
        )
        conn.execute(
            text(
                "DELETE FROM boq_items WHERE tender_id IN (SELECT id FROM tenders WHERE tender_id = :fid)"
            ),
            {"fid": fid},
        )
        conn.execute(text("DELETE FROM boq_comparisons WHERE boq_file_id = :fid"), {"fid": fid})
        conn.execute(text("DELETE FROM tenders WHERE tender_id = :fid"), {"fid": fid})
        conn.commit()
    (Path(settings.BASE_DIR) / "uploads" / f"{fid}.pdf").unlink(missing_ok=True)


def _job_row(job_id: str) -> dict | None:
    with _sync_conn() as conn:
        row = conn.execute(
            text("SELECT status, progress, error, comparison_id FROM boq_jobs WHERE id = :id"),
            {"id": job_id},
        ).fetchone()
    if row is None:
        return None
    return {"status": row[0], "progress": row[1], "error": row[2], "comparison_id": row[3]}


def _stub_delay(monkeypatch) -> None:
    """Broker is not required for submission tests — enqueue is stubbed."""
    from app.workers.tasks import boq_tasks

    monkeypatch.setattr(
        boq_tasks.run_boq_compare_job, "delay", lambda job_id: SimpleNamespace(id="stub-task")
    )


class TestQueueRouting:
    def test_run_boq_compare_job_routes_to_default_queue(self):
        from app.celery_app import celery_app
        from app.workers.tasks.boq_tasks import run_boq_compare_job

        route = celery_app.amqp.router.route({}, run_boq_compare_job.name)
        assert route["queue"].name == "default"


class TestAsyncSubmission:
    def test_compare_returns_202_with_job_id_within_2s(self, monkeypatch):
        monkeypatch.setattr(settings, "BOQ_SYNC_FALLBACK", False)  # env-independent
        _stub_delay(monkeypatch)
        fid = _upload_fixture()
        try:
            with TestClient(app) as client:
                started = time.monotonic()
                response = client.post(
                    "/api/boq/compare",
                    headers=_auth(),
                    data={"boq_file_id": fid, "sor_agency": "BWDB", "zone": "B"},
                )
                elapsed = time.monotonic() - started
            assert response.status_code == 202
            body = response.json()
            assert body["status"] == "PENDING"
            assert body["status_url"] == f"/api/boq/jobs/{body['job_id']}"
            assert elapsed < 2.0, f"submission took {elapsed:.2f}s (acceptance: <2s)"
            assert _job_row(body["job_id"])["status"] == "PENDING"
        finally:
            _cleanup(fid)

    def test_compare_404_for_missing_upload_still_fast(self, monkeypatch):
        _stub_delay(monkeypatch)
        with TestClient(app) as client:
            response = client.post(
                "/api/boq/compare",
                headers=_auth(),
                data={"boq_file_id": "no-such-file", "sor_agency": "BWDB"},
            )
        assert response.status_code == 404

    def test_job_status_unknown_id_is_404(self):
        with TestClient(app) as client:
            response = client.get(f"/api/boq/jobs/{uuid.uuid4()}", headers=_auth())
        assert response.status_code == 404


class TestJobExecution:
    def test_full_async_pipeline_and_sync_parity_on_golden_fixture(self, monkeypatch):
        """Submit → execute task eagerly → poll → result; async output equals the
        sync-fallback output on the golden fixture (T-007 contract)."""
        monkeypatch.setattr(settings, "BOQ_SYNC_FALLBACK", False)  # env-independent
        _stub_delay(monkeypatch)
        fid_async = _upload_fixture()
        fid_sync = _upload_fixture()
        try:
            # One TestClient lifespan for the whole test: app startup reloads
            # SOR rates, so separate lifespans could compare different SOR
            # snapshots — parity is defined for identical inputs.
            with TestClient(app) as client:
                # ── async path ──
                submitted = client.post(
                    "/api/boq/compare",
                    headers=_auth(),
                    data={"boq_file_id": fid_async, "sor_agency": "BWDB", "zone": "B"},
                )
                assert submitted.status_code == 202
                job_id = submitted.json()["job_id"]

                from app.workers.tasks.boq_tasks import run_boq_compare_job

                # The eager task runs in its own asyncio.run() loop (as a real
                # worker would, in its own process). Detach the engine the app's
                # lifespan loop cached so the task builds loop-local connections;
                # later requests lazily rebuild theirs. The detached engine's few
                # idle connections close at process exit (test-only topology).
                import app.db.base as db_base
                import app.db.database as database
                database._engine = None
                database._session_factory = None
                db_base.engine = None
                db_base._session_factory = None

                outcome = run_boq_compare_job.apply(args=[job_id]).get()
                assert outcome["status"] == "SUCCESS", outcome

                row = _job_row(job_id)
                assert row["status"] == "SUCCESS"
                assert row["progress"] == 100
                assert row["comparison_id"]

                status = client.get(f"/api/boq/jobs/{job_id}", headers=_auth()).json()
                assert status["status"] == "SUCCESS"
                assert status["result_url"] == f"/api/boq/jobs/{job_id}/result"
                result = client.get(f"/api/boq/jobs/{job_id}/result", headers=_auth())
                assert result.status_code == 200
                async_payload = result.json()

                # ── sync fallback path (deprecation window) ──
                monkeypatch.setattr(settings, "BOQ_SYNC_FALLBACK", True)
                sync_response = client.post(
                    "/api/boq/compare",
                    headers=_auth(),
                    data={"boq_file_id": fid_sync, "sor_agency": "BWDB", "zone": "B"},
                )
            assert sync_response.status_code == 200
            sync_payload = sync_response.json()

            # ── parity: identical comparison output modulo volatile keys ──
            assert async_payload["total_items"] == GOLDEN["item_count"]
            assert sync_payload["total_items"] == async_payload["total_items"]
            assert sync_payload["summary"] == async_payload["summary"]
            assert sync_payload["data"] == async_payload["data"]
            assert {k: v for k, v in sync_payload.items() if k not in _VOLATILE and k != "data"} == {
                k: v for k, v in async_payload.items() if k not in _VOLATILE and k != "data"
            }
        finally:
            _cleanup(fid_async)
            _cleanup(fid_sync)

    def test_corrupt_pdf_yields_failed_job_with_error(self, monkeypatch):
        monkeypatch.setattr(settings, "BOQ_SYNC_FALLBACK", False)  # env-independent
        _stub_delay(monkeypatch)
        fid = _upload_fixture(content=b"%PDF-corrupt garbage, not parseable")
        try:
            with TestClient(app) as client:
                submitted = client.post(
                    "/api/boq/compare",
                    headers=_auth(),
                    data={"boq_file_id": fid, "sor_agency": "BWDB"},
                )
                assert submitted.status_code == 202
                job_id = submitted.json()["job_id"]

            from app.workers.tasks.boq_tasks import run_boq_compare_job

            outcome = run_boq_compare_job.apply(args=[job_id]).get()
            assert outcome["status"] == "FAILED"

            row = _job_row(job_id)
            assert row["status"] == "FAILED"
            assert row["error"], "FAILED job must carry an error message"

            # result endpoint reports the failure instead of hanging or 500ing
            with TestClient(app) as client:
                result = client.get(f"/api/boq/jobs/{job_id}/result", headers=_auth())
            assert result.status_code == 409
            assert result.json()["detail"]["status"] == "FAILED"
        finally:
            _cleanup(fid)
